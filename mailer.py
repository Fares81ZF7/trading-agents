"""
Construction du rapport HTML et envoi via SMTP Yahoo.
"""

import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import date

YAHOO_USER = os.environ["YAHOO_USER"]          # feh.blidi@yahoo.fr
YAHOO_APP_PASSWORD = os.environ["YAHOO_APP_PASSWORD"]
DEST = os.environ.get("MAIL_DEST", "fh.blidi@gmail.com")

COUL = {"Forte": "#1a7f37", "Moyenne": "#b58105", "Faible": "#6b7280"}


def _lignes(items, sens):
    if not items:
        return f'<tr><td colspan="5" style="padding:8px;color:#6b7280">Aucune recommandation {sens} aujourd\'hui.</td></tr>'
    out = ""
    for it in items:
        c = COUL.get(it.get("conviction", "Faible"), "#6b7280")
        montant = it.get("montant_propose")
        montant_txt = f"{int(montant)} &euro;" if montant is not None else "-"
        out += (
            "<tr>"
            f'<td style="padding:8px;border-bottom:1px solid #eee"><b>{it.get("ticker","")}</b><br>'
            f'<span style="color:#6b7280;font-size:12px">{it.get("nom","")}</span></td>'
            f'<td style="padding:8px;border-bottom:1px solid #eee">{it.get("plateforme","")}</td>'
            f'<td style="padding:8px;border-bottom:1px solid #eee;color:{c};font-weight:600">{it.get("conviction","")}</td>'
            f'<td style="padding:8px;border-bottom:1px solid #eee;text-align:right">{montant_txt}</td>'
            f'<td style="padding:8px;border-bottom:1px solid #eee;font-size:13px">{it.get("justification","")}</td>'
            "</tr>"
        )
    return out


def construire_html(reco: dict, cash: dict) -> str:
    d = date.today().strftime("%d/%m/%Y")
    cash_txt = " &nbsp;|&nbsp; ".join(f"{k} : {v:.2f} &euro;" for k, v in cash.items())
    return f"""<html><body style="font-family:Arial,Helvetica,sans-serif;color:#111;max-width:820px;margin:auto">
<h2 style="margin-bottom:2px">Rapport quotidien - Poche 2</h2>
<div style="color:#6b7280;margin-bottom:4px">{d}</div>
<div style="background:#f3f4f6;padding:8px 12px;border-radius:6px;margin-bottom:18px;font-size:14px">
Cash disponible : {cash_txt}</div>

<h3 style="color:#1a7f37;margin-bottom:6px">Achats (max 5)</h3>
<table style="border-collapse:collapse;width:100%;font-size:14px;margin-bottom:22px">
<tr style="background:#f9fafb;text-align:left">
<th style="padding:8px">Valeur</th><th style="padding:8px">Plateforme</th>
<th style="padding:8px">Conviction</th><th style="padding:8px;text-align:right">Montant</th>
<th style="padding:8px">Justification</th></tr>
{_lignes(reco.get("achats", []), "d'achat")}
</table>

<h3 style="color:#b91c1c;margin-bottom:6px">Ventes / arbitrages (max 5)</h3>
<table style="border-collapse:collapse;width:100%;font-size:14px;margin-bottom:22px">
<tr style="background:#f9fafb;text-align:left">
<th style="padding:8px">Valeur</th><th style="padding:8px">Plateforme</th>
<th style="padding:8px">Conviction</th><th style="padding:8px;text-align:right">Montant</th>
<th style="padding:8px">Justification</th></tr>
{_lignes(reco.get("ventes", []), "de vente")}
</table>

<h3 style="margin-bottom:6px">Contexte marche</h3>
<div style="font-size:14px;background:#f3f4f6;padding:10px 12px;border-radius:6px">
{reco.get("synthese_macro","")}</div>

<div style="color:#9ca3af;font-size:12px;margin-top:22px">
Aide a la decision uniquement. Aucun ordre n'est execute automatiquement.
Recommandations tracees dans Notion (base Agent Trading - Suivi).</div>
</body></html>"""


def envoyer(html: str):
    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"Rapport Poche 2 - {date.today().strftime('%d/%m/%Y')}"
    msg["From"] = YAHOO_USER
    msg["To"] = DEST
    msg.attach(MIMEText(html, "html", "utf-8"))
    with smtplib.SMTP_SSL("smtp.mail.yahoo.com", 465) as s:
        s.login(YAHOO_USER, YAHOO_APP_PASSWORD)
        s.sendmail(YAHOO_USER, [DEST], msg.as_string())
