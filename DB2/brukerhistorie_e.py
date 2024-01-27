import sqlite3
import re

con = sqlite3.connect("database.db")
cursor = con.cursor()

print("KUNDEREGISTERING")
navnInput = input("Oppgi navn: ")

# Innhenting av e-post og sjekk om e-post på riktig format
epostInput = input("Oppgi e-post: ")
emailRegex = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
while not re.fullmatch(emailRegex, epostInput):
    print("Ugyldig e-postadresse. Prøv igjen.")
    epostInput = input("Oppgi e-post: ")

# Innhenting av telefonmumer og sjekk om nummer på riktig format
tlfNr = input("Oppgi telefonnummer: ")
phoneRegex = r'^\d{8}$'
while not re.fullmatch(phoneRegex, tlfNr):
    print("Ugyldig telefonnummer. Prøv igjen.")
    tlfNr = input("Oppgi telefonnummer: ")

# Generere kundeNR
cursor.execute('SELECT MAX(KundeNr) FROM Kunde')
result = cursor.fetchone()[0]
if result is None:
    kundeNr = 1
else:
    kundeNr = result + 1

# Legger først inn kunden i "kunde" med den innhentede kundeinformasjonen
cursor.execute(f"INSERT INTO Kunde (KundeNr, Navn, Epost, Tlf) VALUES ('{kundeNr}', '{navnInput}', '{epostInput}', '{tlfNr}')")

# Legger til kunden i kunderegisteret for alle registrerte operatører
cursor.execute('SELECT Navn FROM Operatør')
operators = cursor.fetchall()
for operator in operators:
    operatorNavn = operator[0]
    cursor.execute(f"INSERT INTO IKundeRegister (KundeNr, OperatørNavn) VALUES ('{kundeNr}', '{operatorNavn}')")

print(f"Kunde med navn {navnInput}, e-post {epostInput} og telefonnummer {tlfNr} ble registrert med kundenummer {kundeNr}")
print(f"NB: skriv ned kundenummeret ditt!")

con.commit()
con.close()
