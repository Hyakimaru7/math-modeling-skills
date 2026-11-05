from pathlib import Path
import csv,itertools,json,math
root=Path(__file__).parent
p=json.loads((root/'problem.json').read_text())
rows=list(csv.DictReader((root/'raw/products.csv').open()))
sol=json.loads((root/'solution.json').read_text())
checks=[]
for f in [.9,1.,1.1]:
    feasible=[]
    for x in itertools.product(*(range(int(r['min_units']),int(r['max_units'])+1) for r in rows)):
        if all(sum(float(r[k])*n for r,n in zip(rows,x))<=cap*f+1e-9 for k,cap in p['resources'].items()):
            feasible.append((sum(float(r['profit'])*n for r,n in zip(rows,x)),x))
    best=max(v for v,x in feasible)
    plans=[x for v,x in feasible if v==best]
    match=next(s for s in sol['tables']['sensitivity'] if s['capacity_factor']==f)
    checks.append({'factor':f,'enumerated_optimum':best,'optimal_plans':plans,'solver_objective':match['objective'],'passed':math.isclose(best,match['objective'])})
result={'passed':all(c['passed'] for c in checks),'checks':checks}
(root/'independent.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(result,ensure_ascii=False,indent=2))
assert result['passed']
