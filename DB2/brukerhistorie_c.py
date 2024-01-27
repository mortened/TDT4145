import sqlite3
from prettytable import PrettyTable

con = sqlite3.connect("database.db")
cursor = con.cursor()

print("Skriv inn ønsket stasjon og ukedag, og finn togruter som går innom stasjonen denne ukedagen")

# Innhenting av ønsket stasjon og sjekk om dette er en faktisk stasjon i databasen
stasjonInput = input("Oppgi stasjon: ")
cursor.execute('SELECT Navn FROM Jernbanestasjon WHERE Navn=?', (stasjonInput,))
result = cursor.fetchone()
while result is None:
    print("Ugyldig stasjon. Prøv igjen.")
    stasjonInput = input("Oppgi stasjon: ")
    cursor.execute('SELECT Navn FROM Jernbanestasjon WHERE Navn=?', (stasjonInput,))
    result = cursor.fetchone()

# Innhenting av ønsket ukedag og sjekk om ukedag eksisterer
ukedagInput = input("Oppgi ukedag (stor første bokstav): ")
ukedager = ["mandag", "tirsdag", "onsdag", "torsdag", "fredag", "lørdag", "søndag"]
while (ukedagInput.lower() not in ukedager):
    print("Ugyldig ukedag. Prøv igjen.")
    ukedagInput = input("Oppgi ukedag: ")


print(f"Togrutene som er innom {stasjonInput} på {ukedagInput} er:")

table = PrettyTable()
table.field_names = ["Rutenavn"]
counter = 0

for row in cursor.execute(f'''SELECT DISTINCT Togrute.Rutenavn
FROM Togrute
JOIN DelstrekningPåTogrute ON Togrute.Rutenavn = DelstrekningPåTogrute.Rutenavn
JOIN Delstrekning ON DelstrekningPåTogrute.DelstrekningID = Delstrekning.DelstrekningID
JOIN Banestrekning ON Delstrekning.BanestrekningNavn = Banestrekning.Navn
NATURAL JOIN Togrutedag
WHERE DelstrekningStart = '{stasjonInput}' OR DelstrekningSlutt = '{stasjonInput}'
AND Togrutedag.Ukedag = '{ukedagInput}';'''):
    table.add_row([row[0]])
    counter += 1

print(table)

if(counter == 0):
    print("Ingen resultat")

con.commit()
con.close()

