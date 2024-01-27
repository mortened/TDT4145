import datetime
import sqlite3
import re
from datetime import date
from prettytable import PrettyTable

con = sqlite3.connect("database.db")
cursor = con.cursor()


# Innhenter kundenummer, og sjekker om kunden allerede er registrert i databasen.
while True:
    kundeNrInput = input("Oppgi ditt kundenummer for å se reisene dine: ")
    cursor.execute("SELECT KundeNr FROM Kunde WHERE KundeNr = ?", (kundeNrInput,))
    exists = cursor.fetchone()
    if exists:
        break
    else:
        print("Ugyldig kundenummer, prøv igjen. Registrer deg som kunde først dersom du ikke har gjort det.")


# Innhenter dagens dato. Implementert slik at sensor skal kunne velge en dato som er før 3. april, slik at togruteforekomstene fremdeles er i fremtiden 
datoInput = input("Oppgi dagens dato / evt. dato du ønsker å hente reiser fra og med [YYYY-MM-DD]: ")
dateRegex = r'^\d{4}-\d{2}-\d{2}$'
while not re.fullmatch(dateRegex, datoInput):
    print("Ugyldig datoformat. Prøv igjen.")
    datoInput = input("Oppgi dato [YYYY-MM-DD]: ")

def getAvgangstidForStasjon(stasjon, rutenavn, dato):
    cursor.execute(f'''
        SELECT StartStasjonPåTogrute.Avgangstid
        FROM StartStasjonPåTogrute
        INNER JOIN Togrute ON StartStasjonPåTogrute.Rutenavn = Togrute.Rutenavn
        INNER JOIN Togruteforekomst ON Togrute.Rutenavn = Togruteforekomst.Rutenavn
        WHERE StartStasjonPåTogrute.Stasjonsnavn = '{stasjon}'
        AND Togrute.Rutenavn = '{rutenavn}'
        AND Togruteforekomst.Dato = '{dato}'

        UNION

        SELECT StopperPåStasjon.Avgangstid
        FROM StopperPåStasjon
        INNER JOIN Togrute ON StopperPåStasjon.Rutenavn = Togrute.Rutenavn
        INNER JOIN Togruteforekomst ON Togrute.Rutenavn = Togruteforekomst.Rutenavn
        WHERE StopperPåStasjon.Stasjonsnavn = '{stasjon}'
        AND Togrute.Rutenavn = '{rutenavn}'
        AND Togruteforekomst.Dato = '{dato}';
    ''')
    tid = cursor.fetchone()
    return tid[0]

def getAnkomsttidForStasjon(stasjon, rutenavn, dato):
    cursor.execute(f'''
        SELECT SluttstasjonPåTogrute.Ankomsttid
        FROM SluttstasjonPåTogrute
        INNER JOIN Togrute ON SluttstasjonPåTogrute.Rutenavn = Togrute.Rutenavn
        INNER JOIN Togruteforekomst ON Togrute.Rutenavn = Togruteforekomst.Rutenavn
        WHERE SluttstasjonPåTogrute.Stasjonsnavn = '{stasjon}'
        AND Togrute.Rutenavn = '{rutenavn}'
        AND Togruteforekomst.Dato = '{dato}'

        UNION

        SELECT StopperPåStasjon.Avgangstid
        FROM StopperPåStasjon
        INNER JOIN Togrute ON StopperPåStasjon.Rutenavn = Togrute.Rutenavn
        INNER JOIN Togruteforekomst ON Togrute.Rutenavn = Togruteforekomst.Rutenavn
        WHERE StopperPåStasjon.Stasjonsnavn = '{stasjon}'
        AND Togrute.Rutenavn = '{rutenavn}'
        AND Togruteforekomst.Dato = '{dato}';
    ''')
    tid = cursor.fetchone()
    return tid[0]


# Finner alle reisene til kunden fra og med oppgitt dato
cursor.execute(f'''
SELECT ko.Ordrenummer, ko.Avgangsdato, ko.Rutenavn,
       CASE
           WHEN sb.SeteNr IS NOT NULL THEN 'Setebillett'
           WHEN gb.SengNr IS NOT NULL THEN 'Sengebillett'
       END AS BillettType,
       CASE WHEN sb.SeteNr IS NOT NULL THEN sb.PåstigningsStasjon ELSE gb.Påstigningsstasjon END AS Påstigningsstasjon,
       CASE WHEN sb.SeteNr IS NOT NULL THEN sb.AvstigningsStasjon ELSE gb.Avstigningsstasjon END AS Avstigningsstasjon,
       CASE WHEN sb.SeteNr IS NOT NULL THEN sb.SeteNr ELSE gb.SengNr END AS Plassnummer,
       vt.Nummer as "Vognnummer"
FROM Kunde k
INNER JOIN Kundeordre ko ON k.KundeNr = ko.KundeNr
LEFT JOIN SeteBillett sb ON ko.Ordrenummer = sb.Ordrenummer
LEFT JOIN SengBillett gb ON ko.Ordrenummer = gb.Ordrenummer
LEFT JOIN VognITogruteforekomst vt ON ko.Avgangsdato = vt.Dato AND ko.Rutenavn = vt.Rutenavn AND (sb.VognID = vt.VognID OR gb.VognID = vt.VognID)
WHERE k.KundeNr = {kundeNrInput}
AND DATE(ko.Avgangsdato) >= DATE({datoInput})
ORDER BY 2 ASC;
''')
               

billettkjøp = cursor.fetchall()


if(len(billettkjøp)==0):
    print("Fant ingen reiser på dette kundenummeret etter denne datoen")
else:
    table = PrettyTable()
    table.field_names = ["Avgangsdato", "Rutenavn", "Billettype", "Avgangsstasjon", "Avgangstid", "Ankomststasjon", "Ankomsttid", "Plassnummer", "Vognnummer"]

    for billett in billettkjøp:
        avgangstid = getAvgangstidForStasjon(billett[4], billett[2], billett[1])
        ankomsttid = getAnkomsttidForStasjon(billett[5], billett[2], billett[1])
        table.add_row([billett[1], billett[2], billett[3], billett[4], avgangstid, billett[5], ankomsttid, billett[6], billett[7]])

    print(table)

con.commit()
con.close()