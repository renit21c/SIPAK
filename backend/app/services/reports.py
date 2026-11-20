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
    """Institutional recommendation, approved by Komdis; not a signed decision."""
    import base64
    from datetime import date
    from reportlab.platypus import Table, TableStyle, Image as PDFImage, PageBreak
    from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
    from reportlab.lib import colors
    from .letterhead import default_letterhead
    output=BytesIO();styles=getSampleStyleSheet()
    styles.add(ParagraphStyle(name='LetterBody',fontName='Times-Roman',fontSize=11,leading=16,alignment=TA_JUSTIFY,spaceAfter=7))
    styles.add(ParagraphStyle(name='LetterSection',fontName='Times-Bold',fontSize=11,leading=16,spaceBefore=12,spaceAfter=7,keepWithNext=True))
    styles.add(ParagraphStyle(name='LetterTitle',fontName='Times-Bold',fontSize=12,leading=17,alignment=TA_CENTER,spaceAfter=4))
    styles.add(ParagraphStyle(name='LetterSmall',fontName='Times-Roman',fontSize=9,leading=13,spaceAfter=5,textColor=HexColor('#4D5361')))
    styles.add(ParagraphStyle(name='LetterSource',parent=styles['LetterSmall'],leftIndent=12))
    styles.add(ParagraphStyle(name='KopName',fontName='Times-Bold',fontSize=13,leading=16,alignment=TA_CENTER))
    styles.add(ParagraphStyle(name='KopUnit',fontName='Times-Bold',fontSize=11,leading=14,alignment=TA_CENTER))
    styles.add(ParagraphStyle(name='KopAddress',fontName='Times-Roman',fontSize=9,leading=12,alignment=TA_CENTER))
    evaluation=case['evaluation'];payload=evaluation['payload'];profile=payload.get('letterhead') or default_letterhead();letter=payload.get('letter') or {}
    def paragraph(value,style='LetterBody'):
        return Paragraph(escape(str(value)).replace('\n','<br/>'),styles[style])
    def logo(key):
        value=profile.get(key,'')
        if not value:return ''
        raw=BytesIO(base64.b64decode(value.split(',',1)[1]));image=PDFImage(raw)
        ratio=min(55/image.imageWidth,65/image.imageHeight);image.drawWidth=image.imageWidth*ratio;image.drawHeight=image.imageHeight*ratio
        return image
    kop=[]
    for key,style in [('parent_name','KopUnit'),('institution_name','KopName'),('unit_name','KopUnit'),('address','KopAddress'),('contact','KopAddress')]:
        if profile.get(key):kop.append(paragraph(profile[key],style))
    width=A4[0]-100
    header=Table([[logo('logo_left'),kop,logo('logo_right')]],colWidths=[64,width-128,64])
    header.setStyle(TableStyle([('VALIGN',(0,0),(-1,-1),'MIDDLE'),('LEFTPADDING',(0,0),(-1,-1),0),('RIGHTPADDING',(0,0),(-1,-1),0),('BOTTOMPADDING',(0,0),(-1,-1),10),('LINEBELOW',(0,0),(-1,-1),1.3,colors.black)]))
    _,header_height=header.wrap(width,A4[1]);top_margin=35+header_height+22
    story=[]
    def para(value,style='LetterBody'):story.append(paragraph(value,style))
    def section(value):para(value,'LetterSection')
    def brand(canvas,doc):
        page_brand(canvas,doc)
        header.wrap(width,A4[1]);header.drawOn(canvas,50,A4[1]-35-header_height)
    para('DOKUMEN REKOMENDASI KOMISI DISIPLIN','LetterTitle')
    para('HASIL TELAAH BERITA ACARA PEMERIKSAAN','LetterTitle');story.append(Spacer(1,13))
    document_date=date.fromisoformat(letter.get('date') or evaluation['created_at'][:10]);months=['Januari','Februari','Maret','April','Mei','Juni','Juli','Agustus','September','Oktober','November','Desember'];date_text=f"{document_date.day} {months[document_date.month-1]} {document_date.year}";place=letter.get('place') or profile.get('place');date_text=(place+', ' if place else '')+date_text
    rows=[['Nomor perkara',':',case['number']],['BAP',':',case['document']['name']],['Tanggal',':',date_text]]
    if letter.get('number'):rows.insert(0,['Nomor surat',':',letter['number']])
    if letter.get('recipient'):rows.append(['Kepada',':',letter['recipient']])
    meta=Table([[paragraph(cell) for cell in row] for row in rows],colWidths=[85,10,width-95]);meta.setStyle(TableStyle([('VALIGN',(0,0),(-1,-1),'TOP'),('LEFTPADDING',(0,0),(-1,-1),0),('RIGHTPADDING',(0,0),(-1,-1),4),('BOTTOMPADDING',(0,0),(-1,-1),2)]));story.append(meta)
    section('I. Ringkasan evaluasi');para(payload['summary'])
    section('II. Dasar pertimbangan');para(payload['basis'])
    for index,article in enumerate(payload.get('articles',[]),1):
        reference=f" ({article['regulation_number']})" if article.get('regulation_number') else ''
        para(f"{index}. {article['regulation_title']} - Pasal {article['number']}{reference}.")
    section('III. Rekomendasi Komdis');para(payload['recommendation'])
    para('Kategori hasil evaluasi: '+payload['category'])
    para('Usulan tindak lanjut / sanksi: '+(payload.get('sanction') or 'Tidak diusulkan dalam evaluasi ini.'))
    story.append(Spacer(1,14));para('Rekomendasi hasil telaah Komdis. Penetapan keputusan mengikuti kewenangan institusi.','LetterSmall')
    # No signature, official seal or invented signatory is generated.
    story.append(PageBreak());para('LAMPIRAN REKOMENDASI KOMISI DISIPLIN','LetterTitle')
    para(f"Perkara {case['number']} | Revisi BAP {case['revision']}",'LetterSmall')
    section('Informasi perkara dan pihak terkait')
    for key,value in case['extraction']['case_information'].items():
        if key!='sources' and value is not None:para(f"{LABELS.get(key,key)}: {value}")
    for source in case['extraction']['case_information'].get('sources',[]):para(f"BAP hal. {source['page']}: {source['quote']}",'LetterSource')
    for person in case['extraction']['involved_persons']:
        para(' | '.join(f"{LABELS.get(k,k)}: {v}" for k,v in person.items() if k!='sources' and v is not None))
        for source in person.get('sources',[]):para(f"BAP hal. {source['page']}: {source['quote']}",'LetterSource')
    if payload.get('articles'):
        section('Pasal dasar pertimbangan yang dipilih Komdis')
        for article in payload['articles']:
            para(f"Pasal {article['number']} - {article['regulation_title']}",'LetterSection')
            import re
            # PDF-extracted line wraps are reflowed within each original clause.
            clauses=[]
            for line in article['text'].splitlines():
                line=line.strip()
                if not line:continue
                if re.match(r'^(?:Pasal \d+|\(\d+\)|[a-z]{1,2}\.\s|BAB\s)',line) or not clauses:clauses.append(line)
                else:clauses[-1]+=' '+line
            for clause in clauses:para(clause)
    section('Telaah ketentuan')
    if not case['analysis']:para('Belum ada hasil pencocokan ketentuan untuk revisi ini. Dasar rekomendasi mengikuti telaah Komdis pada surat utama.')
    for item in case['analysis']:
        para(f"Pasal {item['article']} ayat ({item['paragraph']})"+(f" huruf {item['letter']}" if item['letter'] else '')+f" | {item['version']}",'LetterSection')
        para(item['quote']);para(item['status']);para(item['sanction_basis'])
        if item['missing']:para('Kondisi belum tersedia: '+', '.join(item['missing']))
        for source in item['sources']:para(f"BAP hal. {source['page']}: {source['quote']}",'LetterSource')
    for kind,title in [('evidence','Bukti'),('witnesses','Keterangan saksi'),('chronology','Kronologi')]:
        section(title)
        for item in case['extraction'][kind]:
            for key,value in item.items():
                if key!='sources' and value is not None:para(f"{LABELS.get(key,key)}: {', '.join(map(str,value)) if isinstance(value,list) else value}")
            for source in item.get('sources',[]):para(f"BAP hal. {source['page']}: {source['quote']}",'LetterSource')
        if not case['extraction'][kind]:para('Tidak ditemukan dalam dokumen sumber.','LetterSmall')
    if case['extraction']['missing_information']:
        section('Kelengkapan pemeriksaan')
        for missing in case['extraction']['missing_information']:para(missing)
    section('Pencatatan dokumen')
    para(f"Ditelaah oleh {evaluation['created_by']} | Evaluasi {evaluation['created_at'][:10]} | Revisi {case['revision']}",'LetterSmall')
    if payload.get('ai_draft_id'):para('Draf dibantu AI dan ditelaah Komdis sebelum disimpan.','LetterSmall')
    from ..database import now
    para('Dicetak melalui SIPAK.','LetterSmall')
    SimpleDocTemplate(output,pagesize=A4,leftMargin=50,rightMargin=50,topMargin=top_margin,bottomMargin=57,title='Rekomendasi Komdis - '+case['number'],author=profile.get('institution_name') or 'SIPAK').build(story,onFirstPage=brand,onLaterPages=brand)
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
