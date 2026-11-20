from io import BytesIO
from html import escape
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, KeepTogether
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import A4

def page_brand(canvas,doc):
    canvas.saveState()
    canvas.translate(A4[0]/2,A4[1]/2)
    canvas.rotate(35)
    canvas.setFillColor(HexColor('#F0F1F7'))
    canvas.setFont('Helvetica-Bold',92)
    canvas.drawCentredString(0,0,'SIPAK')
    canvas.restoreState()
    canvas.saveState()
    canvas.setStrokeColor(HexColor('#DFE2ED'))
    canvas.line(42,40,A4[0]-42,40)
    canvas.setFont('Helvetica',8)
    canvas.setFillColor(HexColor('#737A92'))
    canvas.drawString(42,27,'SIPAK | Komisi Disiplin | Dokumen internal')
    canvas.drawRightString(A4[0]-42,27,f'{doc.page}')
    canvas.restoreState()


def generate_recommendation(case,reviewer):
    """A recommendation is the recorded human evaluation, never an AI decision."""
    output=BytesIO(); styles=getSampleStyleSheet()
    styles.add(ParagraphStyle(name='Brand',fontName='Helvetica-Bold',fontSize=25,leading=30,textColor=HexColor('#25285F'),spaceAfter=5))
    styles.add(ParagraphStyle(name='DocumentTitle',fontName='Helvetica-Bold',fontSize=15,leading=21,textColor=HexColor('#25285F'),spaceAfter=16))
    styles['Heading2'].fontSize=12; styles['Heading2'].leading=17
    styles['Heading2'].textColor=HexColor('#25285F');styles['Heading2'].spaceBefore=15
    styles['BodyText'].fontSize=10;styles['BodyText'].leading=15
    styles.add(ParagraphStyle(name='SourceText',fontSize=9,leading=13,textColor=HexColor('#67718C'),leftIndent=12,spaceAfter=6))
    story=[]; evaluation=case['evaluation'];p=evaluation['payload']
    def para(value,style='BodyText'):
        story.append(Paragraph(escape(str(value)).replace('\n','<br/>'),styles[style]));story.append(Spacer(1,5))
    def section(title): para(title,'Heading2')
    para('SIPAK','Brand');para('DOKUMEN REKOMENDASI KOMISI DISIPLIN','DocumentTitle')
    para(f"Nomor perkara: {case['number']} | Revisi BAP: {case['revision']}")
    para(f"BAP: {case['document']['name']} | {case['document']['page_count']} halaman")
    para(f"Evaluator: {evaluation['created_by']} | Evaluasi: {evaluation['created_at'][:10]}")
    para('Rekomendasi hasil telaah Komdis. Penetapan keputusan mengikuti kewenangan institusi.','SourceText')
    section('Ringkasan evaluasi');para(p['summary'])
    section('Rekomendasi Komdis');para(p['recommendation'])
    para(f"Kategori hasil evaluasi: {p['category']}")
    para(f"Usulan tindak lanjut / sanksi: {p.get('sanction') or 'Tidak diusulkan dalam evaluasi ini.'}")
    section('Dasar pertimbangan');para(p['basis'])
    section('Informasi perkara')
    for key,value in case['extraction']['case_information'].items():
        if key!='sources' and value is not None: para(f"{LABELS.get(key,key)}: {value}")
    for source in case['extraction']['case_information'].get('sources',[]): para(f"BAP hal. {source['page']}: {source['quote']}",'SourceText')
    section('Pihak terkait')
    for person in case['extraction']['involved_persons']:
        para(' | '.join(f"{LABELS.get(k,k)}: {v}" for k,v in person.items() if k!='sources' and v is not None))
        for source in person.get('sources',[]): para(f"BAP hal. {source['page']}: {source['quote']}",'SourceText')
    if not case['extraction']['involved_persons']: para('Pihak terkait belum tersedia dalam BAP.')
    section('Telaah ketentuan')
    if not case['analysis']: para('Tidak ada hasil pencocokan ketentuan tersimpan untuk revisi ini. Dasar rekomendasi mengikuti pertimbangan Komdis di atas.')
    for a in case['analysis']:
        para(f"Pasal {a['article']} ayat ({a['paragraph']})"+(f" huruf {a['letter']}" if a['letter'] else '')+f" | {a['version']}")
        para(a['quote']);para(a['status'])
        para(f"Kategori: {a['category'] or 'Belum ditentukan'} | Sanksi hasil pencocokan: {a['sanction'] or 'Belum ditentukan'}")
        para(a['sanction_basis'])
        if a['missing']: para(f"Kondisi belum tersedia: {', '.join(a['missing'])}")
        for source in a['sources']: para(f"BAP hal. {source['page']}: {source['quote']}",'SourceText')
    for kind,title in [('evidence','Bukti'),('witnesses','Keterangan saksi'),('chronology','Kronologi')]:
        section(title)
        if not case['extraction'][kind]: para('Tidak ditemukan dalam dokumen sumber.')
        for item in case['extraction'][kind]:
            for key,value in item.items():
                if key!='sources' and value is not None: para(f"{LABELS.get(key,key)}: {', '.join(map(str,value)) if isinstance(value,list) else value}")
            for source in item.get('sources',[]): para(f"BAP hal. {source['page']}: {source['quote']}",'SourceText')
    section('Kelengkapan dan catatan pemeriksaan')
    for missing in case['extraction']['missing_information']: para(f"Perlu perhatian: {missing}")
    if not case['extraction']['missing_information']: para('Tidak ada kekurangan yang ditandai pada hasil ekstraksi terverifikasi.')
    for r in case['records']:
        if r['kind'] not in ('verification','note','classification_accepted','classification_rejected'): continue
        para(f"{r['created_at'][:10]} | {r['created_by']}: {r['payload'].get('note') or r['payload'].get('text') or '-'}")
    from ..database import now
    section('Pencatatan dokumen')
    para(f"Evaluasi: {evaluation['id']}",'SourceText')
    para(f"Dicetak oleh {reviewer} pada {now()}",'SourceText')
    SimpleDocTemplate(output,pagesize=A4,leftMargin=44,rightMargin=44,topMargin=42,bottomMargin=57,title='Rekomendasi Komdis - '+case['number'],author='SIPAK').build(story,onFirstPage=page_brand,onLaterPages=page_brand)
    return output.getvalue()

LABELS={'case_information':'Informasi perkara','involved_persons':'Pihak yang terlibat','evidence':'Barang bukti','witnesses':'Keterangan saksi','chronology':'Kronologi','relationships':'Hubungan antar pihak','legal_provisions_mentioned':'Ketentuan disebutkan','missing_information':'Informasi belum tersedia','bap_number':'Nomor BAP','examination_date':'Tanggal pemeriksaan','case_type':'Jenis perkara','alleged_category':'Dugaan kategori','incident_date':'Tanggal kejadian','incident_time':'Waktu kejadian','incident_location':'Lokasi kejadian','case_summary':'Ringkasan','name':'Nama','identity_number':'NPP','praja_level':'Tingkat','age':'Umur','gender':'Jenis kelamin','address':'Alamat','campus':'Kampus','role':'Peran','description':'Deskripsi','type':'Jenis','related_person':'Pemilik/pihak terkait','relationship':'Keterkaitan','statement':'Keterangan','date':'Tanggal','time':'Waktu','location':'Lokasi','persons':'Pihak terkait','reference':'Referensi','text':'Isi','subject':'Subjek','relation':'Relasi','object':'Objek'}

def generate_report(case, reviewer):
    output=BytesIO(); styles=getSampleStyleSheet()
    styles.add(ParagraphStyle(name='SIPAK',fontSize=24,textColor=HexColor('#25285F'),spaceAfter=12))
    styles['BodyText'].leading=15
    story=[]
    def para(text,style='BodyText'):
        story.append(Paragraph(escape(str(text)).replace('\n','<br/>'),styles[style])); story.append(Spacer(1,6))
    para('SIPAK','SIPAK'); para('LAPORAN PENGOLAHAN DAN ANALISIS KASUS','Heading2')
    para('ANALISIS PENDAHULUAN â€” BUKAN DOKUMEN KEPUTUSAN RESMI')
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
        para(f"{r['created_at']} Â· {r['created_by']} Â· {r['kind']}")
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
        page_brand(canvas,doc)
    SimpleDocTemplate(output,pagesize=A4,leftMargin=40,rightMargin=40,topMargin=40,bottomMargin=45).build(story,onFirstPage=footer,onLaterPages=footer)
    return output.getvalue()
