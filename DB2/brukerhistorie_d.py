import sqlite3
import re
from prettytable import PrettyTable

con = sqlite3.connect("database.db")
cursor = con.cursor()

# Innhenter startstasjon og sjekker om stasjonen finnes i databasen
startInput = input("Oppgi startstasjon: ")
cursor.execute('SELECT Navn FROM Jernbanestasjon WHERE Navn=?', (startInput,))
result = cursor.fetchone()
while result is None:
    print("Ugyldig startstasjon. Prøv igjen.")
    startInput = input("Oppgi startstasjon: ")
    cursor.execute('SELECT Navn FROM Jernbanestasjon WHERE Navn=?', (startInput,))
    result = cursor.fetchone()

# Innhenter sluttstasjon og sjekker om stasjonen finnes i databasen
sluttInput = input("Oppgi sluttstasjon: ")
cursor.execute('SELECT Navn FROM Jernbanestasjon WHERE Navn=?', (sluttInput,))
result = cursor.fetchone()
while result is None:
    print("Ugyldig sluttstasjon. Prøv igjen.")
    sluttInput = input("Oppgi sluttstasjon: ")
    cursor.execute('SELECT Navn FROM Jernbanestasjon WHERE Navn=?', (sluttInput,))
    result = cursor.fetchone()

# Innhenter ønsket reisedato og sjekker om gyldig datoformat
datoInput = input("Oppgi dato [YYYY-MM-DD]: ")
dateRegex = r'^\d{4}-\d{2}-\d{2}$'
while not re.fullmatch(dateRegex, datoInput):
    print("Ugyldig datoformat. Prøv igjen.")
    datoInput = input("Oppgi dato [YYYY-MM-DD]: ")

# Innhenter ønsket klokkeslett og sjekker om gyldig klokkeslettformat
klokkeslettInput = input("Oppgi klokkeslett [HH:MM]: ")
timeRegex = r'^([01]\d|2[0-3]):([0-5]\d)$'
while not re.fullmatch(timeRegex, klokkeslettInput):
    print("Ugyldig klokkeslettformat. Prøv igjen.")
    klokkeslettInput = input("Oppgi klokkeslett [HH:MM]: ")
    
cursor.execute(f'''
   SELECT Togrute.Rutenavn,Togruteforekomst.Dato,
       StartStasjon.Avgangstid AS StartTid,
       SluttStasjon.Ankomsttid AS SluttTid 
FROM Togrute 
JOIN (
    SELECT Rutenavn,
           Stasjonsnavn,
           Avgangstid 
      FROM StartStasjonPåTogrute 
     UNION 
    SELECT Rutenavn,
           Stasjonsnavn,
           Ankomsttid AS Avgangtid 
      FROM SluttStasjonPåTogrute 
     UNION 
    SELECT Rutenavn,
           Stasjonsnavn,
           Avgangstid 
      FROM StopperPåStasjon ) StartStasjon ON StartStasjon.Rutenavn = Togrute.Rutenavn 

JOIN (
    SELECT Rutenavn,
           Stasjonsnavn,
           Ankomsttid
      FROM SluttStasjonPåTogrute 
     UNION 
    SELECT Rutenavn,
           Stasjonsnavn,
           Avgangstid  
      FROM StopperPåStasjon ) SluttStasjon ON SluttStasjon.Rutenavn = Togrute.Rutenavn 

JOIN Togruteforekomst ON  Togruteforekomst.Rutenavn =  Togrute.Rutenavn 
WHERE StartStasjon.Stasjonsnavn ='{startInput}' 
AND SluttStasjon.Stasjonsnavn ='{sluttInput}' 
AND ((DATE(Togruteforekomst.Dato) = DATE('{datoInput}') AND TIME(StartStasjon.Avgangstid) >= TIME('{klokkeslettInput}') ) OR DATE(Togruteforekomst.Dato) = DATE('{datoInput}','+1 day')) 
AND ((StartStasjon.Stasjonsnavn < SluttStasjon.Stasjonsnavn AND Kjøreretning=0  ) OR (StartStasjon.Stasjonsnavn > SluttStasjon.Stasjonsnavn AND Kjøreretning=1)) 
ORDER BY 2 ASC ,3 ASC;
''')

rows = cursor.fetchall()
if(len(rows)==0):
    print("Søket ditt ga ingen resultater..")
else:
    print("Oversikt over togruter mellom ønsket start- og sluttstasjon:")
    table = PrettyTable()
    table.field_names = ["Rute", "Dato", f"Avgang {startInput}", f"Ankomst {sluttInput}"]
    for row in rows:
        table.add_row(row)

    print(table)
        
con.commit()
con.close()