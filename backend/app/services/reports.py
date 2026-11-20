from io import BytesIO
from html import escape
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, KeepTogether
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import A4

LABELS={'case_information':'Informasi perkara','involved_persons':'Pihak yang terlibat','evidence':'Barang bukti','witnesses':'Keterangan saksi','chronology':'Kronologi','relationships':'Hubungan antar pihak','legal_provisions_mentioned':'Ketentuan disebutkan','missing_information':'Informasi belum tersedia','bap_number':'Nomor BAP','examination_date':'Tanggal pemeriksaan','case_type':'Jenis perkara','alleged_category':'Dugaan kategori','incident_date':'Tanggal kejadian','incident_time':'Waktu kejadian','incident_location':'Lokasi kejadian','case_summary':'Ringkasan','name':'Nama','identity_number':'NPP','praja_level':'Tingkat','age':'Umur','gender':'Jenis kelamin','address':'Alamat','campus':'Kampus','role':'Peran','description':'Deskripsi','type':'Jenis','related_person':'Pemilik/pihak terkait','relationship':'Keterkaitan','statement':'Keterangan','date':'Tanggal','time':'Waktu','location':'Lokasi','persons':'Pihak terkait','reference':'Referensi','text':'Isi','subject':'Subjek','relation':'Relasi','object':'Objek'}

def generate_report(case, reviewer):
    output=BytesIO(); styles=getSampleStyleSheet()
    styles.add(ParagraphStyle(name='SIPAK',fontSize=24,textColor=HexColor('#25285F'),spaceAfter=12))
    styles['BodyText'].leading=15
    story=[]
    def para(text,style='BodyText'):
        story.append(Paragraph(escape(str(text)).replace('\n','<br/>'),styles[style])); story.append(Spacer(1,6))
    para('SIPAK','SIPAK'); para('LAPORAN PENGOLAHAN DAN ANALISIS KASUS','Heading2')
    para('ANALISIS PENDAHULUAN — BUKAN DOKUMEN KEPUTUSAN RESMI')
    para(f"Perkara: {case['number']} | Revisi: {case['revision']}")
    para(f"Dokumen: {case['document']['name']} | {case['document']['page_count']} halaman")
    para(f"Verifikasi manusia: {'Terverifikasi' if case['verified'] else 'Menunggu pemeriksaan'}")
    for kind,value in case['extraction'].items():
        para(LABELS.get(kind,kind),'Heading2')
        items=[value] if isinstance(value,dict) else value
        if not items: para('Tidak ditemukan dalam dokumen')
        for item in items:
            if isinstance(item,str): para(item); continue
            for key,val in item.items():
                if key=='sources':
                    for s in val: para(f"Sumber halaman {s['page']}: {s['quote']}")
                elif val is not None: para(f"{LABELS.get(key,key)}: {', '.join(map(str,val)) if isinstance(val,list) else val}")
    para('Analisis ketentuan dan rekomendasi awal','Heading2')
    if not case['analysis']: para('Belum cukup informasi untuk menentukan kecocokan ketentuan.')
    for a in case['analysis']:
        para(f"Pasal {a['article']} ayat {a['paragraph']} huruf {a['letter']} | Versi {a['version']}")
        para(a['quote']); para(a['status']); para(f"Kategori: {a['category'] or 'Belum ditentukan'}; sanksi awal: {a['sanction'] or 'Belum ditentukan'}")
        para(a['sanction_basis']); para(f"Informasi kurang: {', '.join(a['missing']) or '-'}")
    para('Catatan pemeriksaan manusia','Heading2')
    for r in case['records']:
        payload=r['payload']
        para(f"{r['created_at']} · {r['created_by']} · {r['kind']}")
        para(payload.get('note') or payload.get('text') or 'Catatan proses tersimpan.')
        if r['kind']=='workflow':
            para(f"Tahap: {payload['stage']+1}; tanggal: {payload['date']}; penanggung jawab: {payload['responsible']}")
        if r['kind']=='verification':
            para(f"Revisi: {payload['revision']}; disetujui: {'Ya' if payload['approved'] else 'Belum'}")
    para('Catatan keputusan resmi','Heading2')
    if not case['decisions']: para('Belum ada keputusan resmi yang dicatat.')
    for d in case['decisions']:
        para(f"{d['number']} | {d['date']} | {d['official']}"); para(d['sanction']); para(d['basis']); para(d['reason'])
    from ..database import now
    para(f'Dibuat oleh: {reviewer} | Waktu: {now()}')
    def footer(canvas,doc):
        canvas.setFont('Helvetica',8); canvas.setFillColor(HexColor('#77788B'))
        canvas.drawString(36,25,'SIPAK · Rahasia · Penilaian AI memerlukan pemeriksaan manusia')
        canvas.drawRightString(A4[0]-36,25,f'Halaman {doc.page}')
    SimpleDocTemplate(output,pagesize=A4,leftMargin=40,rightMargin=40,topMargin=40,bottomMargin=45).build(story,onFirstPage=footer,onLaterPages=footer)
    return output.getvalue()
