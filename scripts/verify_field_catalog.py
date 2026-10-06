"""Validate the catalog offline using only the Python standard library.

Implements only the JSON Schema keywords present in the bundled schema; rejects
unknown keywords. This is not a general-purpose JSON Schema implementation.
Book bindings detect selected literal/value drift, not all semantic errors.
External URLs are checked for source identity/shape, not fetched by this command.
"""

from collections import Counter
import copy
from datetime import date
import json
import re
from urllib.parse import urlsplit, unquote

from doc_utils import content_lines, headings, links, local_target
from r4_support import ROOT, local_path, pointer, sha

KEYWORDS={"$schema","$defs","$ref","title","description","type","required","properties",
          "additionalProperties","items","minItems","minLength","pattern","enum","const","minimum"}


def check_schema_keywords(node):
    if set(node)-KEYWORDS:
        raise ValueError("unsupported schema keywords: "+str(set(node)-KEYWORDS))
    for k in ("properties","$defs"):
        for child in node.get(k,{}).values():check_schema_keywords(child)
    if "items" in node:check_schema_keywords(node["items"])


def validate_shape(value, schema, root, at="$"):
    if "$ref" in schema:
        if not schema["$ref"].startswith("#/"):
            raise ValueError("only local schema refs supported")
        return validate_shape(value,pointer(root,schema["$ref"][1:]),root,at)
    types=schema.get("type",[])
    types=[types] if isinstance(types,str) else types
    actual=("null" if value is None else "boolean" if type(value) is bool else
            "integer" if type(value) is int else "number" if type(value) is float else
            "object" if isinstance(value,dict) else "array" if isinstance(value,list) else
            "string" if isinstance(value,str) else "invalid")
    if types and actual not in types and not(actual=="integer" and "number" in types):
        raise ValueError(f"{at}: type {actual} not in {types}")
    if "enum" in schema and not any(type(v) is type(value) and v==value for v in schema["enum"]):
        raise ValueError(f"{at}: invalid enum")
    if "const" in schema and (type(value) is not type(schema["const"]) or value != schema["const"]):
        raise ValueError(f"{at}: invalid const")
    if isinstance(value,dict):
        missing=set(schema.get("required",[]))-set(value)
        extra=set(value)-set(schema.get("properties",{}))
        if missing or (extra and schema.get("additionalProperties") is False):
            raise ValueError(f"{at}: missing={missing}, extra={extra}")
        for k,s in schema.get("properties",{}).items():
            if k in value:validate_shape(value[k],s,root,at+"/"+k)
    if isinstance(value,list):
        if len(value)<schema.get("minItems",0):raise ValueError(f"{at}: too few items")
        for i,v in enumerate(value):validate_shape(v,schema["items"],root,at+f"/{i}")
    if isinstance(value,str):
        if len(value)<schema.get("minLength",0):raise ValueError(f"{at}: empty string")
        if "pattern" in schema and not re.search(schema["pattern"],value):raise ValueError(f"{at}: pattern")
    if type(value) in (int,float) and "minimum" in schema and value<schema["minimum"]:
        raise ValueError(f"{at}: below minimum")


def book_target(link):
    name,sep,fragment=link.partition("#")
    path=local_path(name)
    if path.suffix!=".md" or not path.is_file():raise ValueError("missing book: "+link)
    text=path.read_text(encoding="utf-8")
    if sep and unquote(fragment) not in {h[3] for h in headings(text)}:
        raise ValueError("missing anchor: "+link)
    return text


def version(value):
    return tuple(map(int,value.split(".")))


def validate_semantics(catalog, check_files=True):
    ids=set()
    allowed={"counter":{"cumulative","delta","from_payload"},"gauge":{"instant"},
             "histogram":{"from_payload"},"dynamic":{"from_query"},
             "state":{"not_applicable"},"identifier":{"not_applicable"},"timestamp":{"not_applicable"}}
    conversions={("ms","s"):(1,1000), ("us","s"):(1,1000000), ("ns","s"):(1,1000000000),
                 ("ps","s"):(1,10**12), ("proc_kB","By"):(1024,1),
                 ("sector512","By"):(512,1), ("percent","ratio"):(1,100)}
    runtime={("USER_HZ","s"):"SC_CLK_TCK", ("interval","s"):"SQL interval to seconds",
             ("k8s_quantity","By"):"Kubernetes Quantity parser"}
    trusted={"dev.mysql.com","docs.aws.amazon.com","docs.kernel.org","github.com","raw.githubusercontent.com",
             "kubernetes.io","v1-35.docs.kubernetes.io","man7.org","opentelemetry.io","www.postgresql.org","protobuf.dev"}
    for f in catalog["fields"]:
        name=f["id"]
        if name in ids:raise ValueError("duplicate id: "+name)
        ids.add(name)
        if f["temporality"] not in allowed[f["kind"]]:raise ValueError("kind/temporality: "+name)
        if f["reset"]["wrap_bits"] is not None and (f["kind"]!="counter" or f["temporality"]!="cumulative"):
            raise ValueError("wrap on non-cumulative field: "+name)
        n=f["normalization"]
        if (n["mode"]=="runtime") != (n["runtime_parameter"] is not None):
            raise ValueError("runtime conversion parameter: "+name)
        u=f["unit"]
        pair=(u["raw"],u["normalized"])
        if pair in conversions and (n["numerator"],n["denominator"])!=conversions[pair]:
            raise ValueError("unit scale: "+name)
        if pair in conversions and n["mode"]!="rational":raise ValueError("conversion mode: "+name)
        if pair in runtime and (n["mode"]!="runtime" or n["runtime_parameter"]!=runtime[pair]):
            raise ValueError("runtime unit conversion: "+name)
        if pair[0]!=pair[1] and pair not in conversions and pair not in runtime and pair!=("By_or_max","By"):
            raise ValueError("unmapped unit conversion: "+name)
        if n["mode"]=="identity" and (n["numerator"],n["denominator"])!=(1,1):
            raise ValueError("identity scale: "+name)
        a=f["availability"]
        if a["min_inclusive"] and a["max_exclusive"] and version(a["min_inclusive"])>=version(a["max_exclusive"]):
            raise ValueError("empty version range: "+name)
        if a["introduced_in"] and a["removed_in"] and version(a["introduced_in"])>=version(a["removed_in"]):
            raise ValueError("invalid source lifecycle: "+name)
        if a["introduced_in"] and a["min_inclusive"] and version(a["min_inclusive"])<version(a["introduced_in"]):
            raise ValueError("review range precedes field introduction: "+name)
        if a["removed_in"] and a["max_exclusive"] and version(a["max_exclusive"])>version(a["removed_in"]):
            raise ValueError("review range extends after removal: "+name)
        for url in f["references"]["primary"]:
            p=urlsplit(url)
            if p.scheme!="https" or p.hostname not in trusted or p.username or p.password or not p.path:
                raise ValueError("not a primary HTTPS URL: "+url)
        if not check_files:continue
        for link in f["references"]["book"]:book_target(link)
        for e in f["evidence"]:
            path=local_path(e["path"])
            data=path.read_bytes()
            if sha(data)!=e["sha256"]:raise ValueError("evidence hash: "+e["path"])
            if e["selector_kind"]=="json_pointer":pointer(json.loads(data),e["locator"])
    date.fromisoformat(catalog["reviewed_on"])
    if check_files:
        book=json.loads((ROOT/"book.json").read_text(encoding="utf-8"))
        if book["edition"]!=catalog["book_edition"]:raise ValueError("book/catalog edition drift")
        lookup={f["id"]:f for f in catalog["fields"]}
        for guard in catalog["book_checks"]:
            value=pointer(lookup[guard["field_id"]],guard["pointer"])
            if type(value) is not type(guard["expected"]) or value!=guard["expected"]:
                raise ValueError("catalog guard drift: "+str(guard))
            if guard["contains"] not in book_target(guard["book"]):
                raise ValueError("book text drift: "+str(guard))


def negative_checks(catalog,schema):
    def change(path,value):
        def mutate(d):
            parent,key=path.rsplit("/",1)
            item=pointer(d,parent)
            if isinstance(item,list):item[int(key)]=value
            else:item[key]=value
        return mutate
    trials=[lambda d:d["fields"][0].pop("unit"),
            change("/fields/0/kind","sum"),change("/fields/0/unit/raw","ticks-of-some-kind"),
            change("/fields/0/temporality","instant"),change("/fields/0/normalization/denominator",0),
            change("/fields/0/normalization/runtime_parameter",None),
            change("/fields/0/unit/normalized","By"),
            change("/fields/0/permissions/mutates_target",True),
            change("/fields/0/availability/min_inclusive","not-a-version"),
            lambda d:d["fields"].append(copy.deepcopy(d["fields"][0])),
            change("/fields/0/references/primary",["https://example.com/unverified"]),
            change("/fields/0/references/book",["../outside.md"]),
            change("/fields/0/references/book",["docs/scope.md#missing-anchor"]),
            lambda d:d["book_checks"][0].update(expected=64),
            lambda d:d["fields"][0].update(availability=dict(d["fields"][0]["availability"],min_inclusive="6.12",introduced_in="6.13")),
            lambda d:d["fields"][3]["evidence"][0].update(sha256="0"*64)]
    for i,mutate in enumerate(trials):
        bad=copy.deepcopy(catalog);mutate(bad)
        try:
            validate_shape(bad,schema,schema)
            validate_semantics(bad)
        except (ValueError,KeyError,FileNotFoundError):continue
        raise AssertionError(f"negative check {i} was not rejected")
    return len(trials)


def check_supporting_documents(catalog):
    count=0
    for name in ("catalog/README.md","review/claude-codex-r4.md"):
        source=local_path(name)
        text=source.read_text(encoding="utf-8")
        if "\ufffd" in text:raise ValueError("invalid document encoding: "+name)
        for _,line in content_lines(text):
            for _,_,destination in links(line):
                target=local_target(source,destination)
                if target is None:continue
                path,fragment=target
                if not path.resolve().is_relative_to(ROOT) or not path.is_file():
                    raise ValueError("missing/outside supporting link: "+destination)
                if fragment and path.suffix==".md":
                    book_target(path.relative_to(ROOT).as_posix()+"#"+fragment)
                count+=1
    receipt=json.loads((ROOT/"review/field-catalog-source-links.json").read_text(encoding="utf-8"))
    urls={u for f in catalog["fields"] for u in f["references"]["primary"]}
    if {r["url"] for r in receipt["results"]}!=urls:
        raise ValueError("external link review does not cover catalog URLs")
    return count


def main():
    catalog=json.loads((ROOT/"catalog/field-catalog.json").read_text(encoding="utf-8"))
    schema=json.loads((ROOT/"catalog/field-catalog.schema.json").read_text(encoding="utf-8"))
    check_schema_keywords(schema)
    validate_shape(catalog,schema,schema)
    validate_semantics(catalog)
    count=negative_checks(catalog,schema)
    link_count=check_supporting_documents(catalog)
    print(f"PASS: {len(catalog['fields'])} catalog fields {dict(Counter(f['domain'] for f in catalog['fields']))}")
    print(f"PASS: schema/types/units/temporality, local links, evidence hashes/selectors, {len(catalog['book_checks'])} book bindings, {count} rejection cases")
    print(f"PASS: {link_count} supporting document links; external source URL inventory matches saved availability review")
    print("Primary URL shape/source identity checked offline; HTTP availability and prose truth are separate reviews.")


if __name__=="__main__":main()
