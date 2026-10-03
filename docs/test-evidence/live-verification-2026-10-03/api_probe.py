import json,urllib.request,sys
B="http://localhost:5050"
def call(m,p,body=None):
    d=json.dumps(body).encode() if body is not None else None
    r=urllib.request.Request(B+p,data=d,method=m,headers={"Content-Type":"application/json"})
    try:
        x=urllib.request.urlopen(r); return x.status,json.loads(x.read() or b"null")
    except urllib.error.HTTPError as e:
        return e.code,json.loads(e.read() or b"null")
prompts=["A modern website for my bakery called Sweet Crumbs with a menu, gallery and contact form",
"Portfolio for a freelance developer named Arjun Rao with projects and contact, dark colors",
"An online coding school called CodeNest with pricing and FAQ",
"asdf qwerty","what is the capital of France","hola quiero un sitio web para mi panadería",
"I took a selfie at the beach yesterday and my cat looks funny in it lol","best bakery in France",
"<script>alert(1)</script>"]
for p in prompts:
    s,j=call("POST","/api/generate",{"prompt":p})
    r=j.get("requirements") if s==201 else j
    print(s,repr(p[:60])); print(json.dumps(r)[:900]); print()
print("empty",call("POST","/api/generate",{"prompt":"   "}))
print("missing",call("POST","/api/generate",{}))
print("long",call("POST","/api/generate",{"prompt":"bakery "*3000})[1])
print("badjson",call("POST","/api/generate",None))
print("unknown get",call("GET","/api/projects/99999"))
print("unknown put",call("PUT","/api/projects/99999",{"model":{}}))
print("unknown del",call("DELETE","/api/projects/99999"))
print("unknown export",call("GET","/api/projects/99999/export")[0])
print("unknown dup",call("POST","/api/projects/99999/duplicate"))
print("unknown regen",call("POST","/api/projects/99999/regenerate",{"prompt":"bakery"}))
