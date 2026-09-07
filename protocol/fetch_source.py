import json, urllib.request, urllib.parse

titles = ["Қазақстан", "Абай Құнанбайұлы", "Астана", "Алматы",
          "Қазақ тілі", "Қазақ хандығы", "Мұхтар Әуезов", "Тұран"]

out = []
for t in titles:
    q = urllib.parse.urlencode({"action": "query", "prop": "extracts",
                                "explaintext": "1", "format": "json",
                                "redirects": "1", "titles": t})
    req = urllib.request.Request("https://kk.wikipedia.org/w/api.php?" + q,
                                 headers={"User-Agent": "qolda-bench/1.0"})
    d = json.load(urllib.request.urlopen(req))
    for p in d["query"]["pages"].values():
        e = p.get("extract", "")
        if e:
            out.append(e)
            print(f"{t}: {len(e.split())} words")

text = "\n\n".join(out)
open("source_kk.txt", "w", encoding="utf-8").write(text)
print("TOTAL:", len(text.split()), "words")
