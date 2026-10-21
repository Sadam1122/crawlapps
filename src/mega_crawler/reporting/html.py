import html
import json


def render(path, manifest, analysis, records, registry):
    payload = (
        json.dumps(
            {"manifest": manifest, "analysis": analysis, "records": records, "registry": registry},
            ensure_ascii=False,
        )
        .replace("<", "\\u003c")
        .replace(">", "\\u003e")
        .replace("&", "\\u0026")
    )
    template = PathTemplate()
    path.write_text(
        template.replace("__LABEL__", html.escape(manifest["label"])).replace(
            "__PAYLOAD__", payload
        ),
        encoding="utf-8",
    )


def PathTemplate():
    return r"""<!doctype html><html lang="id"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Gold Competitor Intelligence Indonesia</title>
<style>
:root{font-family:system-ui;color:#173340;background:#f3f6f8}body{margin:0}header{padding:28px 4%;background:#113847;color:white}h1{font-size:26px;margin:5px 0}.badge{display:inline-block;background:#f4c75c;color:#172e3a;padding:6px 12px;border-radius:5px;font-weight:700}.wrap{padding:20px 4%}aside{background:#fff1cd;padding:16px;border-left:5px solid #d6a32b}section{background:white;padding:20px;margin:16px 0;border-radius:8px}.filters{display:flex;gap:12px;flex-wrap:wrap}label{display:grid;font-size:13px;gap:5px}select,input{padding:8px;border:1px solid #a7bcc9;border-radius:4px}.kpis{display:flex;gap:12px;flex-wrap:wrap}.kpi{padding:18px;background:#e8f1f5;flex:1;min-width:160px}.kpi strong{display:block;font-size:24px}.table{max-height:480px;overflow:auto}table{border-collapse:collapse;width:100%;font-size:12px}td,th{text-align:left;padding:9px;border-bottom:1px solid #dae3e8;vertical-align:top;min-width:100px;max-width:360px;overflow-wrap:anywhere}th{position:sticky;top:0;background:#e5eef3}a{color:#006998}.muted{color:#527083;font-size:13px}summary{cursor:pointer}nav a{color:white;margin-right:14px}button{padding:8px;background:#174d61;color:white;border:0;border-radius:4px}
</style><header><div class="badge">__LABEL__</div><h1>Gold Competitor Intelligence · Indonesia</h1><p>Pemasaran emas dalam sampel teramati · Asia/Jakarta</p><nav><a href="#mentah">Data & ketersediaan</a><a href="#peringkat">Peringkat</a><a href="#isu">Isu</a><a href="#produk">Produk</a></nav></header>
<main class="wrap"><aside id="limits"></aside><section><div class="filters" id="filters"></div><p class="muted">Filter memilih baris post dan data terkait. Peringkat tersimpan selalu menampilkan cohort dan periode asal; filter brand tidak menghitung ulang peringkat.</p></section><div class="kpis" id="kpis"></div>
<section id="mentah"><h2>Post teramati dan bukti</h2><div id="posts"></div><h3>Snapshot metrik mentah</h3><p class="muted">N/A = tidak tersedia, berbeda dari nol teramati. observed: terlihat; hidden: disembunyikan; not_exposed: tidak dibuka sumber; requires_permission: perlu izin; request_failed: permintaan gagal; not_collected: belum dikumpulkan. Status dan definisi berlaku per snapshot.</p><div id="snapshots"></div><h3>Ketersediaan metrik dan cakupan</h3><div id="availability"></div><div id="coverage"></div></section>
<section id="peringkat"><h2>Peringkat dimensi yang eligible</h2><p id="mandiri"></p><p class="muted">ER views = (likes atau reactions yang setara + comments) / views × 100. Median ER dihitung per post; pooled ER = total interaksi / total views × 100. Gate eksploratif: jumlah post, ketersediaan metrik, dan jumlah brand sesuai manifest. Format, umur konten dan periode harus sebanding.</p><div id="rankings"></div><details><summary>Alasan gate dan ukuran sampel</summary><div id="gates"></div></details><p class="muted">Tidak ada composite jika dimensi bersama tidak lengkap. Rank hanya untuk sampel teramati; bukan peringkat pasar nasional.</p></section>
<section><h2>Tren snapshot</h2><div id="trends"></div><h2>Tema, hook dan CTA</h2><div id="content"></div></section>
<section id="isu"><h2>Isu dan sentimen terhadap aspek emas</h2><p class="muted">Preliminary / belum divalidasi manusia. Volume komentar terpilih, bukan incidence nasabah.</p><div id="issues"></div><h3>Earned share of conversation pada korpus teramati</h3><div id="conversation"></div></section>
<section id="produk"><h2>Fakta produk dan biaya</h2><div id="facts"></div><h3>Pemetaan kompetitor dan status verifikasi</h3><div id="registry"></div></section>
<section><h2>Rekomendasi berbasis bukti</h2><div id="recommendations"></div><p>Jika bukti belum memadai, tindak lanjut adalah verifikasi akun, hak akses, tanggal aktif produk dan pengumpulan sampel yang sebanding.</p><h3>Manifest dan kesalahan pengumpulan</h3><div id="errors"></div><details><summary>Manifest audit</summary><pre id="manifest"></pre></details></section></main>
<script type="application/json" id="payload">__PAYLOAD__</script><script>
'use strict';const D=JSON.parse(document.getElementById('payload').textContent),R=D.records,A=D.analysis,M=D.manifest;
const $=id=>document.getElementById(id);const esc=x=>String(x??'N/A').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
function val(v){if(v===null||v===undefined)return 'N/A';if(Array.isArray(v))return v.map(val).join('<br>');if(typeof v==='object')return Object.entries(v).map(([k,x])=>esc(k)+': '+val(x)).join('<br>');let s=String(v);if(/^https?:\/\//.test(s)){try{let u=new URL(s);if(['http:','https:'].includes(u.protocol)&&!u.username&&!u.password)return '<a target="_blank" rel="noopener noreferrer" href="'+esc(u.href)+'">Buka sumber ↗</a>'}catch{}}return esc(s)}
const wib=t=>t?new Intl.DateTimeFormat('id-ID',{dateStyle:'medium',timeStyle:'short',timeZone:'Asia/Jakarta'}).format(new Date(t))+' WIB':'N/A';
function table(id,rows,cols){if(!rows.length){$(id).innerHTML='<p class="muted">Belum tersedia / tidak memenuhi filter atau gate. Nilai kosong tidak diisi nol.</p>';return}cols=cols||[...new Set(rows.flatMap(r=>Object.keys(r)))];$(id).innerHTML='<div class="table"><table><thead><tr>'+cols.map(c=>'<th>'+esc(c)+'</th>').join('')+'</tr></thead><tbody>'+rows.map(r=>'<tr>'+cols.map(c=>'<td>'+val(r[c])+'</td>').join('')+'</tr>').join('')+'</tbody></table></div>'}
const productMap=Object.fromEntries(D.registry.map(r=>[r.product_id,r]));const fields=[['platform','Platform'],['brand_id','Brand'],['segment','Segmen'],['ownership_type','Kepemilikan'],['format','Format']];
function attr(p,key){return key==='brand_id'||key==='segment'?(productMap[p.product_id]||{})[key]:p[key]}
for(const [key,label] of fields){let vals=[...new Set(R.master_posts.map(p=>attr(p,key)).filter(Boolean))].sort();let l=document.createElement('label');l.textContent=label;let s=document.createElement('select');s.id='f_'+key;s.innerHTML='<option value="">Semua</option>'+vals.map(v=>'<option>'+esc(v)+'</option>').join('');s.onchange=update;l.append(s);$('filters').append(l)}
for(const [key,label] of [['start','Mulai WIB (inklusif)'],['end','Akhir WIB (eksklusif)']]){let l=document.createElement('label');l.textContent=label;let i=document.createElement('input');i.type='date';i.id='f_'+key;i.onchange=update;l.append(i);$('filters').append(l)}
$('limits').textContent=M.label+' | Status run: '+M.status+' | Freshness: '+wib(M.finished_at_utc)+' | Periode ['+wib(M.window_start)+', '+wib(M.window_end)+') | '+A.limitations.join(' ');$('mandiri').textContent=A.mandiri_status;$('manifest').textContent=JSON.stringify(M,null,2);
function update(){let selected=Object.fromEntries(fields.map(([k])=>[k,$('f_'+k).value]));let start=$('f_start').value,end=$('f_end').value;let posts=R.master_posts.filter(p=>fields.every(([k])=>!selected[k]||attr(p,k)===selected[k])&&(!start||(p.published_at_utc&&Date.parse(p.published_at_utc)>=Date.parse(start+'T00:00:00+07:00')))&&(!end||(p.published_at_utc&&Date.parse(p.published_at_utc)<Date.parse(end+'T00:00:00+07:00'))));let ids=new Set(posts.map(p=>p.platform+':'+p.post_id));let related=r=>ids.has(r.platform+':'+r.post_id);let brands=new Set(posts.map(p=>attr(p,'brand_id')));let platforms=new Set(posts.map(p=>p.platform));
$('kpis').innerHTML=[['Post teramati',posts.length],['Snapshot',R.metric_snapshots.filter(related).length],['Brand dalam post',brands.has(undefined)?brands.size-1:brands.size]].map(([k,v])=>'<div class="kpi">'+esc(k)+'<strong>'+esc(v)+'</strong></div>').join('');
table('posts',posts.map(p=>({...p,waktu_terbit:wib(p.published_at_utc)})),['platform','post_id','product_id','format','waktu_terbit','relevance_score','ownership_type','title','text','canonical_url','evidence_hash']);table('snapshots',R.metric_snapshots.filter(related).map(o=>({...o,waktu_observasi:wib(o.observed_at_utc)})),['platform','post_id','waktu_observasi','values','metric_status','count_precision','metric_definition_version','source_url']);table('availability',A.raw_availability.filter(related));table('coverage',R.source_coverage.filter(r=>!selected.platform||r.platform===selected.platform));
const rankFilter=r=>fields.every(([k])=>!selected[k]||r[k]===selected[k]);const periodChanged=!!(start||end);table('rankings',periodChanged?[]:R.platform_rankings.filter(rankFilter));table('gates',periodChanged?[]:A.ranking_gates.filter(r=>!selected.brand_id||r.brand_id===selected.brand_id));table('trends',A.trends.filter(related));table('content',A.content_analysis.filter(related));
table('issues',selected.brand_id||selected.segment||selected.ownership_type||selected.format||periodChanged?[]:R.issue_summary.filter(r=>platforms.has(r.platform)));table('conversation',periodChanged||selected.segment||selected.ownership_type||selected.format?[]:A.observed_conversation.filter(r=>(!selected.platform||r.platform===selected.platform)&&(!selected.brand_id||r.brand_id===selected.brand_id)));table('facts',R.product_comparison.filter(r=>!selected.brand_id||(productMap[r.product_id]||{}).brand_id===selected.brand_id));table('registry',D.registry.filter(r=>(!selected.brand_id||r.brand_id===selected.brand_id)&&(!selected.segment||r.segment===selected.segment)),['brand_name','product_name','segment','active_status','verification_status','regulatory_status','verification_sources']);table('recommendations',A.recommendations);table('errors',R.collection_errors)}update();
</script></html>"""
