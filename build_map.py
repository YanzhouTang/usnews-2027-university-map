#!/usr/bin/env python3
"""Rebuild the KML/GeoJSON map from bundled public data (standard library only)."""
from pathlib import Path
from collections import Counter
import json
import xml.etree.ElementTree as ET
ROOT=Path(__file__).resolve().parent
NS='http://www.opengis.net/kml/2.2'
ET.register_namespace('',NS)
TIERS=[(10,'TOP10','A52714'),(30,'TOP30','FF5252'),(50,'TOP50','F9A825'),(100,'TOP100','FFEA00'),(200,'TOP200','BDBDBD')]
DISPLAY_FIELDS=['2027 USNEWS Ranking','Chinese name','English name','City / State','2026 USNEWS Ranking']
def el(p,t,text=None,**a):
    n=ET.SubElement(p,'{%s}%s'%(NS,t),a)
    if text is not None: n.text=str(text)
    return n
def kml(rows,title):
    root=ET.Element('{%s}kml'%NS); d=el(root,'Document'); el(d,'name',title)
    for _,label,color in TIERS:
        icon=el(el(d,'Style',id=label),'IconStyle'); el(icon,'color','ff'+color[4:6]+color[2:4]+color[:2]); el(icon,'scale',1.1)
        el(el(icon,'Icon'),'href','https://www.gstatic.com/mapspro/images/stock/503-wht-blank_maps.png')
    for _,label,_ in TIERS:
        group=[r for r in rows if r['tier']==label]
        if not group: continue
        folder=el(d,'Folder'); el(folder,'name',label)
        for r in group:
            p=el(folder,'Placemark'); el(p,'name',f"{r['rank']}. {r['zh']} {r['canonical_name']}")
            fields={'2027 USNEWS Ranking':str(r['rank'])+('（并列）' if r['tied'] else ''),'Chinese name':r['zh'],'English name':r['canonical_name'],'City / State':r['city']+', '+r['state_code'],'2026 USNEWS Ranking':r['rank2026'] if r['rank2026'] is not None else '原图未收录'}
            el(p,'styleUrl','#'+label)
            ext=el(p,'ExtendedData')
            for k,v in fields.items(): el(el(ext,'Data',name=k),'value',v)
            el(el(p,'Point'),'coordinates',f"{r['longitude']:.6f},{r['latitude']:.6f},0")
    ET.indent(root,space='  ')
    return ET.tostring(root,encoding='utf-8',xml_declaration=True)
def main():
    ranks=json.loads((ROOT/'data/rankings_enriched.json').read_text()); coords={r['name']:r for r in json.loads((ROOT/'data/coordinates.json').read_text())}
    assert len(ranks)==len({r['name'] for r in ranks})==201
    rows=[]
    for r in ranks:
        c=coords[r['name']]; assert c['rank']==r['rank'] and 1<=r['rank']<=200
        assert 18<=c['latitude']<=72 and -180<=c['longitude']<=-60
        row=dict(r,**{k:c[k] for k in ['latitude','longitude','unitid','city','street','zip','coordinate_source','coordinate_year','official_name']})
        row.update(state_code=c['state'],tier=next(t[1] for t in TIERS if r['rank']<=t[0]),change=None if r['rank2026'] is None else r['rank2026']-r['rank']); rows.append(row)
    assert len({r['unitid'] for r in rows})==201
    counts=Counter(r['tier'] for r in rows)
    (ROOT/'usnews-2027-top200.kml').write_bytes(kml(rows,'2027 USNEWS TOP200美国大学分布地图'))
    (ROOT/'layers').mkdir(exist_ok=True)
    for _,label,_ in TIERS: (ROOT/'layers'/f'{label}.kml').write_bytes(kml([r for r in rows if r['tier']==label],label))
    (ROOT/'universities-2027.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2))
    features=[{'type':'Feature','geometry':{'type':'Point','coordinates':[r['longitude'],r['latitude']]},'properties':{k:v for k,v in r.items() if k not in ['longitude','latitude']}} for r in rows]
    (ROOT/'universities-2027.geojson').write_text(json.dumps({'type':'FeatureCollection','features':features},ensure_ascii=False,indent=2))
    for f in [ROOT/'usnews-2027-top200.kml',*sorted((ROOT/'layers').glob('*.kml'))]:
        places=ET.parse(f).findall('.//{%s}Placemark'%NS)
        assert len(places)==(201 if f.parent==ROOT else counts[f.stem])
        for p in places:
            assert p.find('{%s}description'%NS) is None
            assert [x.get('name') for x in p.findall('{%s}ExtendedData/{%s}Data'%(NS,NS))]==DISPLAY_FIELDS
    print(json.dumps({'total':len(rows),'layers':dict(counts),'coordinate_coverage':'201/201','with_2026_comparison':sum(r['rank2026'] is not None for r in rows)},ensure_ascii=False))
if __name__=='__main__': main()
