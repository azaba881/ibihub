"""Génération du contrat de bail PDF (ReportLab)."""

from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import Image, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


def render_reservation_contract_pdf_bytes(reservation) -> bytes:
    """Retourne le PDF binaire pour une réservation confirmée."""
    r = reservation
    e = r.entrepot
    proprio = e.proprietaire
    client = r.client

    out = BytesIO()
    doc = SimpleDocTemplate(
        out,
        pagesize=A4,
        leftMargin=1.6 * cm,
        rightMargin=1.6 * cm,
        topMargin=1.6 * cm,
        bottomMargin=1.6 * cm,
        title=f'Contrat IbiHub Reservation #{r.pk}',
    )

    styles = getSampleStyleSheet()
    title = ParagraphStyle(
        'ibihub_title',
        parent=styles['Heading1'],
        fontSize=16,
        textColor=colors.HexColor('#0d5c4d'),
        spaceAfter=8,
    )
    h2 = ParagraphStyle(
        'ibihub_h2',
        parent=styles['Heading2'],
        fontSize=12,
        textColor=colors.HexColor('#0d5c4d'),
        spaceBefore=10,
        spaceAfter=6,
    )
    body = ParagraphStyle('ibihub_body', parent=styles['BodyText'], fontSize=10, leading=14)

    def meta_table(rows):
        t = Table(rows, colWidths=[5.6 * cm, 10.8 * cm])
        t.setStyle(
            TableStyle(
                [
                    ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                    ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#d1d5db')),
                    ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f6faf8')),
                    ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, -1), 9.5),
                    ('LEFTPADDING', (0, 0), (-1, -1), 6),
                    ('RIGHTPADDING', (0, 0), (-1, -1), 6),
                    ('TOPPADDING', (0, 0), (-1, -1), 5),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
                ]
            )
        )
        return t

    story = []
    story.append(Paragraph('IbiHub', ParagraphStyle('logo', parent=styles['Heading2'], textColor=colors.HexColor('#0d5c4d'))))
    story.append(Paragraph('Contrat de mise a disposition d\'espace de stockage', title))
    story.append(Paragraph(f'Reference reservation n° <b>{r.pk}</b>', body))
    story.append(Spacer(1, 10))

    story.append(Paragraph('Parties', h2))
    story.append(
        meta_table(
            [
                ['Bailleur / Exploitant', f"{proprio.get_full_name() or proprio.username}<br/>E-mail : {proprio.email or proprio.username}"],
                ['Locataire / Client', f"{client.get_full_name() or client.username}<br/>E-mail : {client.email or client.username}"],
            ]
        )
    )

    story.append(Paragraph('Lieu et objet', h2))
    story.append(
        meta_table(
            [
                ['Designation', e.titre],
                ['Adresse', f'{e.adresse}, {e.get_ville_display()}'],
                ['Surface', f'{e.surface_m2} m²'],
            ]
        )
    )

    story.append(Paragraph('Conditions financieres et periode', h2))
    story.append(
        meta_table(
            [
                ['Date de debut', r.date_debut.strftime('%d/%m/%Y')],
                ['Date de fin', r.date_fin.strftime('%d/%m/%Y')],
                ['Montant total', f'{r.montant_total} FCFA'],
                ['Frais plateforme', f"{r.frais_assurance} FCFA ({r.taux_commission_display})"],
                ['Caution', f'{r.montant_caution} FCFA'],
            ]
        )
    )

    if r.inventaire_depot:
        story.append(Paragraph('Inventaire declare par le locataire', h2))
        story.append(Paragraph(r.inventaire_depot.replace('\n', '<br/>'), body))

    story.append(Paragraph('Clause de responsabilite', h2))
    story.append(
        Paragraph(
            "Le locataire demeure responsable du contenu stocke et de la conformite reglementaire des biens. "
            "Le bailleur et IbiHub ne sont pas responsables des pertes, vols, degradations ou dommages indirects "
            "sauf faute lourde prouvee. Ce document est genere automatiquement a titre d\'annexe informative.",
            body,
        )
    )
    etat = getattr(r, 'etat_des_lieux', None)
    if etat and (etat.photo_entree_1 or etat.photo_entree_2):
        story.append(PageBreak())
        story.append(Paragraph('Etat des lieux - Entree', h2))
        story.append(Paragraph('Photos d entree jointes au dossier', body))
        for img_field in (etat.photo_entree_1, etat.photo_entree_2):
            if img_field and getattr(img_field, 'path', None):
                try:
                    story.append(Spacer(1, 6))
                    story.append(Image(img_field.path, width=13 * cm, height=8 * cm))
                except Exception:
                    continue

    doc.build(story)
    return out.getvalue()


def render_reservation_ticket_pdf_bytes(reservation) -> bytes:
    """Ticket court 1 page : prix, dates, code d'accès."""
    r = reservation
    out = BytesIO()
    doc = SimpleDocTemplate(
        out,
        pagesize=A4,
        leftMargin=2 * cm,
        rightMargin=2 * cm,
        topMargin=2 * cm,
        bottomMargin=2 * cm,
        title=f'Ticket IbiHub #{r.pk}',
    )
    styles = getSampleStyleSheet()
    title = ParagraphStyle('t_title', parent=styles['Heading1'], fontSize=22, textColor=colors.HexColor('#0d5c4d'))
    big = ParagraphStyle('t_big', parent=styles['Heading2'], fontSize=28, textColor=colors.HexColor('#111827'), spaceAfter=8)
    normal = ParagraphStyle('t_n', parent=styles['BodyText'], fontSize=12, leading=18)
    story = [
        Paragraph('IbiHub - Ticket de depot', title),
        Spacer(1, 8),
        Paragraph(f'Reservation #{r.pk}', normal),
        Paragraph(f'Code d acces: <b>{r.code_court or "-"}</b>', big),
        Spacer(1, 4),
        Paragraph(f'Prix total: <b>{r.montant_total} FCFA</b>', big),
        Spacer(1, 6),
        Paragraph(f'Dates: <b>{r.date_debut.strftime("%d/%m/%Y")} - {r.date_fin.strftime("%d/%m/%Y")}</b>', normal),
        Paragraph(f'Entrepot: <b>{r.entrepot.titre}</b>', normal),
        Paragraph('Presentez ce ticket au proprietaire pour un acces rapide.', normal),
    ]
    doc.build(story)
    return out.getvalue()
