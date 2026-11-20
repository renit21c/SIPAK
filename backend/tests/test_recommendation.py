import fitz
from backend.tests.test_sipak import verify


def evaluation(case,**changes):
    return {'outcome':'proceed','summary':'Data sintetis sudah ditelaah terhadap sumber BAP.','recommendation':'Lengkapi pembinaan berdasarkan hasil rapat Komdis sintetis.','basis':'Pertimbangan sintetis dengan mengacu pada BAP halaman satu.','category':'Belum ditentukan','sanction':'','expected_revision':case['revision'],'expected_assessment_id':case['latest_assessment_id'],**changes}


def test_verified_evaluation_to_watermarked_recommendation(case,client):
    path='/api/cases/'+case['id']
    assert client.get(path+'/recommendation').status_code==409
    assert client.post(path+'/evaluation',json=evaluation(case)).status_code==409
    c=verify(client,case)
    assert client.post(path+'/evaluation',json=evaluation(c,basis='   ')).status_code==422
    result=client.post(path+'/evaluation',json=evaluation(c))
    assert result.status_code==200,result.text
    assert result.json()['recommendation_ready']
    response=client.get(path+'/recommendation')
    assert response.status_code==200 and response.content.startswith(b'%PDF-')
    with fitz.open(stream=response.content,filetype='pdf') as pdf:
        assert len(pdf)>=2
        for page in pdf:
            # The large rotated watermark is separate from the header/footer logo.
            assert any(s['text']=='SIPAK' and s['size']>80 for b in page.get_text('dict')['blocks'] if 'lines' in b for line in b['lines'] for s in line['spans'])
        text=' '.join(p.get_text() for p in pdf)
        assert 'DOKUMEN REKOMENDASI KOMISI DISIPLIN' in text
        assert 'Budi Uji' in text and 'BAP hal. 1' in text
        assert 'Lengkapi pembinaan' in text
        assert 'Dasar pertimbangan' in text


def test_revise_returns_to_verification_and_supersedes_ready_pdf(case,client):
    c=verify(client,case);path='/api/cases/'+c['id']
    assert client.post(path+'/evaluation',json=evaluation(c)).status_code==200
    revised=client.post(path+'/evaluation',json=evaluation(c,outcome='revise',summary='Identitas sintetis perlu diperiksa ulang.')).json()
    assert not revised['verified'] and not revised['recommendation_ready']
    assert client.get(path+'/recommendation').status_code==409
    assert client.post(path+'/evaluation',json=evaluation(revised)).status_code==409
    reverified=verify(client,revised)
    assert not reverified['recommendation_ready']
    assert client.post(path+'/evaluation',json=evaluation(reverified)).status_code==200


def test_changes_require_new_evaluation_and_stale_tabs_are_rejected(case,client):
    c=verify(client,case);path='/api/cases/'+c['id']
    assert client.post(path+'/evaluation',json=evaluation(c)).status_code==200
    analysis=client.post(path+'/analysis',json={'facts':{},'note':'Belum ada fakta tambahan yang bersumber.'})
    assert analysis.status_code==200
    assert client.get(path+'/recommendation').status_code==409
    assert client.post(path+'/evaluation',json=evaluation(c)).status_code==409
    updated=client.get(path).json()
    assert client.post(path+'/evaluation',json=evaluation(updated)).status_code==200
    assert client.get(path+'/recommendation').status_code==200
    corrected=verify(client,updated)
    assert client.get(path+'/recommendation').status_code==409
    assert client.post(path+'/evaluation',json=evaluation(updated)).status_code==409
    assert client.post(path+'/evaluation',json=evaluation(corrected)).status_code==200
    # Old generic notes cannot bypass the evaluation prerequisites.
    assert client.post(path+'/notes',json={'kind':'commission_recommendation','text':'Rekomendasi lewat endpoint catatan lama.'}).status_code==409
