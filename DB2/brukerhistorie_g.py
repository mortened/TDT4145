import datetime
import sqlite3
import re
from prettytable import PrettyTable

con = sqlite3.connect("database.db")
cursor = con.cursor()

def reverse_tuple(t):
    new_tuple = ()
    for i in range(len(t)-1, -1, -1):
        new_tuple += (t[i],)
    return new_tuple

def finn_alle_delstrekninger(start, slutt, rutenavn, hovedretning):
    #Rekursiv spørring som finner alle delstrekninger mellom vilkårlig start- og sluttstasjon
    cursor.execute("""
        WITH RECURSIVE RouteStations AS (
        SELECT 
            Delstrekning.DelstrekningStart,
            Delstrekning.DelstrekningSlutt,
            1 AS StationOrder
        FROM Delstrekning
        JOIN DelstrekningPåTogrute ON Delstrekning.DelstrekningID = DelstrekningPåTogrute.DelstrekningID
        WHERE DelstrekningPåTogrute.Rutenavn = ? AND Delstrekning.DelstrekningStart = ?

        UNION ALL

        SELECT 
            Delstrekning.DelstrekningStart,
            Delstrekning.DelstrekningSlutt,
            RouteStations.StationOrder + 1 AS StationOrder
        FROM Delstrekning
        JOIN DelstrekningPåTogrute ON Delstrekning.DelstrekningID = DelstrekningPåTogrute.DelstrekningID
        JOIN RouteStations ON RouteStations.DelstrekningSlutt = Delstrekning.DelstrekningStart
        WHERE DelstrekningPåTogrute.Rutenavn = ? AND RouteStations.DelstrekningSlutt != ?
        ),
        StationOrders AS (
        SELECT DelstrekningStart, DelstrekningSlutt, StationOrder
        FROM RouteStations
        WHERE StationOrder <= (
            SELECT MIN(StationOrder)
            FROM RouteStations
            WHERE DelstrekningSlutt = ?
        )
        ORDER BY StationOrder
        )
        SELECT DelstrekningStart, DelstrekningSlutt
        FROM StationOrders;
    """, (rutenavn, start, rutenavn, slutt, slutt))
    resultat = cursor.fetchall()
    #Reveserer delstrekningtuplene (start, slutt) og rekkefølgen på delstrekningene dersom hovedretningen er "bakover", altså sørover
    if(hovedretning==0):
        resultat2 = []
        for r in resultat:
            r = reverse_tuple(r)
            resultat2.append(r)
        resultat2.reverse()
        resultat = resultat2
    
    return resultat

def finn_ledige_billetter(dato, startstasjon, sluttstasjon):

    # Finn togruteforekomster med hovedretning som passer med dato
    cursor.execute(f"""
        SELECT Togruteforekomst.Rutenavn, Togrute.Kjøreretning
        FROM Togruteforekomst
		Inner join Togrute on Togruteforekomst.Rutenavn = Togrute.Rutenavn
        WHERE Togruteforekomst.Dato = '{dato}'
    """)
    togruteforekomster = cursor.fetchall()

    #Finner delstrekninger mellom start- og sluttstasjon på togruteforekomstene
    togruteforekomster_delstrekninger = []
    for togruteforekomst in togruteforekomster:
        if(togruteforekomst[1]==0):
            togruteforekomster_delstrekninger.append(finn_alle_delstrekninger(sluttstasjon,startstasjon,togruteforekomst[0],togruteforekomst[1] ))
        else:
            togruteforekomster_delstrekninger.append(finn_alle_delstrekninger(startstasjon,sluttstasjon,togruteforekomst[0],togruteforekomst[1]))
    
    #Finner aktuelle delstrekninger på reisen til bruker, samt alle aktuelle togruteforekomster som inneholder strekningen
    aktuelle_delstrekninger = []
    aktuelle_togruteforekomster = []
    for i,rute in enumerate(togruteforekomster_delstrekninger):
        for tuppel in rute:
            if (tuppel[0] == startstasjon):
                if(rute not in aktuelle_delstrekninger):
                    aktuelle_delstrekninger.append(rute)
                if(togruteforekomster[i] not in aktuelle_togruteforekomster):
                    aktuelle_togruteforekomster.append(togruteforekomster[i])


    #Finner alle seter, og vognen til setene på aktuelle togruteforekomster
    ledige_seter = []
    for i, togrute in enumerate(aktuelle_togruteforekomster):
        cursor.execute(f'''
            Select Sete.SeteNr, VognITogruteforekomst.Nummer
            from Sete 
            inner join Vogntype on Vogntype.Navn = Sete.VogntypeNavn
            inner join Vogn on Vogntype.Navn = Vogn.VogntypeNavn
            Inner join VognITogruteforekomst on Vogn.VognID = VognITogruteforekomst.VognID
            Where VognITogruteforekomst.Rutenavn='{togrute[0]}'
            AND VognITogruteforekomst.Dato = '{dato}';

        ''')
        ledige_seter.append([])
        ledige_seter[i].append(cursor.fetchall())
        ledige_seter[i].append(togrute[0])

    #Finner opptatte setebilletter på de aktuelle togruteforekomstene
    opptatt_sete = []
    for togrute in aktuelle_togruteforekomster:
        cursor.execute(f'''
            SELECT Distinct Sete.SeteNr, VognITogruteforekomst.Nummer, SeteBillett.PåstigningsStasjon, SeteBillett.AvstigningsStasjon, Togrute.Kjøreretning
            FROM Sete
            Inner JOIN SeteBillett ON SeteBillett.SeteNr = Sete.SeteNr
            Inner JOIN Kundeordre ON Kundeordre.Ordrenummer = SeteBillett.Ordrenummer
            Inner JOIN Vogn ON Vogn.VognID = SeteBillett.VognID
            Inner JOIN VognITogruteforekomst ON Vogn.VognID = VognITogruteforekomst.VognID
			Inner Join Togruteforekomst on Togruteforekomst.Rutenavn = Kundeordre.Rutenavn
			Inner Join Togrute on Togrute.Rutenavn = Togruteforekomst.Rutenavn
            WHERE Kundeordre.Rutenavn = '{togrute[0]}'
            AND Kundeordre.Avgangsdato = '{dato}';

        ''')
        opptatt_sete.append(cursor.fetchall())
    
    #Finner alle senger på de aktuelle togruteforekomstene
    alle_senger = []
    for i, togrute in enumerate(aktuelle_togruteforekomster):
        cursor.execute(f'''
            Select Seng.SengNr, VognITogruteforekomst.Nummer
            from Seng 
            inner join Vogntype on Vogntype.Navn = Seng.VogntypeNavn
            inner join Vogn on Vogntype.Navn = Vogn.VogntypeNavn
            Inner join VognITogruteforekomst on Vogn.VognID = VognITogruteforekomst.VognID
            Where VognITogruteforekomst.Rutenavn='{togrute[0]}'
            AND VognITogruteforekomst.Dato = '{dato}';
        ''')
        alle_senger.append([])
        alle_senger[i].append(cursor.fetchall())
        alle_senger[i].append(togrute[0])
    
    #Finner opptatte sengebilletter på de aktuelle togruteforekomstene:
    opptatt_seng = []
    for togrute in aktuelle_togruteforekomster:
        cursor.execute(f'''
            SELECT Distinct Seng.SengNr, VognITogruteforekomst.Nummer, SengBillett.PåstigningsStasjon, SengBillett.AvstigningsStasjon, Togrute.Kjøreretning, Kundeordre.KundeNr
            FROM Seng
            Inner JOIN SengBillett ON SengBillett.SengNr = Seng.SengNr
            Inner JOIN Kundeordre ON Kundeordre.Ordrenummer = SengBillett.Ordrenummer
            Inner JOIN Vogn ON Vogn.VognID = SengBillett.VognID
            Inner JOIN VognITogruteforekomst ON Vogn.VognID = VognITogruteforekomst.VognID
			Inner Join Togruteforekomst on Togruteforekomst.Rutenavn = Kundeordre.Rutenavn
			Inner Join Togrute on Togrute.Rutenavn = Togruteforekomst.Rutenavn
            WHERE Kundeordre.Rutenavn = '{togrute[0]}'
            AND Kundeordre.Avgangsdato = '{dato}';
        ''')
        opptatt_seng.append(cursor.fetchall())
    
    #Finner alle senger som kunden har kjøpt fra før
    opptatt_seng_av_kunde = []
    for togrute in aktuelle_togruteforekomster:
        cursor.execute(f'''
            SELECT Distinct Seng.SengNr, VognITogruteforekomst.Nummer
            FROM Seng
            Inner JOIN SengBillett ON SengBillett.SengNr = Seng.SengNr
            Inner JOIN Kundeordre ON Kundeordre.Ordrenummer = SengBillett.Ordrenummer
            Inner JOIN Vogn ON Vogn.VognID = SengBillett.VognID
            Inner JOIN VognITogruteforekomst ON Vogn.VognID = VognITogruteforekomst.VognID
			Inner Join Togruteforekomst on Togruteforekomst.Rutenavn = Kundeordre.Rutenavn
			Inner Join Togrute on Togrute.Rutenavn = Togruteforekomst.Rutenavn
            WHERE Kundeordre.Rutenavn = '{togrute[0]}'
            AND Kundeordre.Avgangsdato = '{dato}'
            AND Kundeordre.KundeNr = '{kundeNr}';

        ''')
        opptatt_seng_av_kunde.append(cursor.fetchall())
    
    
#Fjerner opptatte senger fra listen med alle senger
    ledige_senger = []
    for i, togrute in enumerate(aktuelle_togruteforekomster):
        temp_ledige_senger = list(alle_senger[i][0])

        for opptatt in opptatt_seng:
            for seng in opptatt:
                seng_tuple = (seng[0], seng[1])  # Convert the string to an integer
                if seng_tuple in temp_ledige_senger:
                    temp_ledige_senger.remove(seng_tuple)

        ledige_senger.append((temp_ledige_senger, togrute[0]))

    
    #Finner hvilke delstrekninger de opptatte Setene er opptatt på
    opptatt_sete_paa_delstrekning = []
    for i, sete_elementer in enumerate(opptatt_sete):
        opptatt_sete_paa_delstrekning.append([])
        for j, sete_element in enumerate(sete_elementer):
            opptatt_sete_paa_delstrekning[i].append([])
            opptatt_sete_paa_delstrekning[i][j].append(sete_element[0])
            opptatt_sete_paa_delstrekning[i][j].append(sete_element[1])
            hovedretning = sete_element[4]
            if(hovedretning==0):
                opptatt_sete_paa_delstrekning[i][j].append(finn_alle_delstrekninger(sete_element[3],sete_element[2],aktuelle_togruteforekomster[i][0],hovedretning))
            else:
                opptatt_sete_paa_delstrekning[i][j].append(finn_alle_delstrekninger(sete_element[2],sete_element[3],aktuelle_togruteforekomster[i][0],hovedretning))
            opptatt_sete_paa_delstrekning[i][j].append(hovedretning)
    
    #Fjerner opptatte seter fra ledige seter setet er opptatt på del av reisen til brukeren
    for i, togrute in enumerate(aktuelle_togruteforekomster):
        for j, opptatt_sete in enumerate(opptatt_sete_paa_delstrekning[i]):
            for k, delstrekning in enumerate(opptatt_sete[2]):
                #Sjekker om en delstrekning på ruten til bruker finnes på ruten til en setebillett
                if(delstrekning in aktuelle_delstrekninger[0]):
                    #Fjerner setet dersom det er opptatt
                    if((opptatt_sete[0],opptatt_sete[1]) in ledige_seter[i][0]):
                        ledige_seter[i][0].remove((opptatt_sete[0],opptatt_sete[1]))

    #Fjerner togruteforekomster uten ledige seter og senger:
    for i, togrute in enumerate(aktuelle_togruteforekomster):
        if(len(ledige_seter[i][0])==0):
            aktuelle_togruteforekomster.remove(togrute)
    
    
    if len(aktuelle_togruteforekomster) == 0:
        print("Dessverre må vi som togrutefinnetjeneste meddele at det er ingen tog som går denne strekningen/dagen :( ")
        return

    
    #Håndterer billettvalg for seter
    seteArray = []
    for i, togrute in enumerate(aktuelle_togruteforekomster):
        if(len(ledige_seter[i][0])!=0):
            fortsett = True
            togrutesvar = ""
            antallSeterSvar = 0
            seteArray.append([])
            seteArray[i].append(togrute[0])
            #Printer ut ledige seter:
            print(f"Ledige seter på {togrute[0]} (SeteNr, VognNr):")
            for ledig_sete in ledige_seter[i][0]:
                print(ledig_sete)
            while fortsett:
                togrutesvar = input(f"Ønsker du å kjøpe sete på {togrute[0]}? (Ja/Nei): ")
                if togrutesvar.lower() in ["ja", "nei"]:
                    fortsett = False
                else:
                    print("Vennligst svar Ja eller Nei")
            if(togrutesvar.lower() == "ja"):
                fortsett = True
                while fortsett:
                    antallSeterSvar = input(f"Hvor mange seter ønsker du å kjøpe (0-{len(ledige_seter[i][0])})? ")
                    if(antallSeterSvar.isnumeric()):
                        antallseter = int(antallSeterSvar)
                        if (0 <= antallseter <= len(ledige_seter[i][0])):
                            fortsett = False
                    else:
                        print(f"Vennligst svar med et tall mellom 0 og {len(ledige_seter[i][0])}.")
                for j in range(0,antallseter):
                    fortsett = True
                    while fortsett:
                        pattern = r"\(\d+,\s*\d+\)"
                        valgt_sete = input("Oppgi sete på formen SeteNr, VognNr: ")
                        valgt_sete = "(" + valgt_sete.replace(" ", "") + ")" 
                        if(re.match(pattern,valgt_sete)):
                            valgt_sete_tuple = eval(valgt_sete)
                            if valgt_sete_tuple in seteArray[i][1:]:
                                print("Du har allerede valgt dette setet!")
                            elif(valgt_sete_tuple in ledige_seter[i][0]):
                                seteArray[i].append(valgt_sete_tuple)
                                print(f"Du valgte {valgt_sete_tuple}")
                                if(j!=antallseter-1):
                                    print(f"Du har nå {antallseter-1-j} sete(r) igjen å velge")
                                fortsett = False
                            else:
                                print("Ugyldig sete")
                        else:
                            print("Prøv på nytt")
    
    #Kjøper setebilletter dersom brukeren har valgt sete(r)
    if any(len(sublist) > 1 for sublist in seteArray):
        kjopSeteBilletter(seteArray, dato, startstasjon, sluttstasjon)


     # Håndtere billettvalg for senger
    sengArray = []
    for i, togrute in enumerate(aktuelle_togruteforekomster):
        if len(ledige_senger[i][0]) != 0:
            fortsett = True
            togrutesvar = ""
            antallSengerSvar = 0
            sengArray.append([])
            sengArray[i].append(togrute[0])
            while fortsett:
                togrutesvar = input(f"Ønsker du å kjøpe seng på {togrute[0]}? (Ja/Nei): ")
                if togrutesvar.lower() in ["ja", "nei"]:
                    fortsett = False
                else:
                    print("Vennligst svar Ja eller Nei")
            if(togrutesvar.lower() == "ja"):
                # La brukeren velge kupeen
                kupeer = {}
                for seng in ledige_senger[i][0]:
                    kupe_nr = (int(seng[0]) - 1) // 2 + 1
                    vogn_nr = int(seng[1])
                    if (kupe_nr, vogn_nr) not in kupeer:
                        kupeer[(kupe_nr, vogn_nr)] = []
                    kupeer[(kupe_nr, vogn_nr)].append(seng)
                
                print("Ledige kupeer:")
                while not fortsett:
                    for (kupe_nr, vogn_nr), senger in kupeer.items():
                        print(f"Kupe {kupe_nr} i vogn {vogn_nr} ({len(senger)} ledige senger)")
                    valgt_kupee, valgt_vogn = map(int, input("Velg kupeen og vognen du vil kjøpe senger fra slik: KupeNr, VognNr ").split(","))
                    ledige_senger_i_kupee = kupeer.get((valgt_kupee, valgt_vogn), [])

                    if not validerSengeBilletter(ledige_senger_i_kupee, opptatt_seng_av_kunde):
                        continue
                    fortsett = True
                while fortsett:
                    print("Ledige senger i valgt kupe og vogn (SengNr, VognNr):")
                    for ledig_seng in ledige_senger_i_kupee:
                        print(ledig_seng)
                    
                    antallSengerSvar = input(f"Hvor mange senger ønsker du å kjøpe i kupeen, det er {len(ledige_senger_i_kupee)} senger ledige? ")
                    if(antallSengerSvar.isnumeric()):
                        antall_senger = int(antallSengerSvar)
                        if (1 <= antall_senger <= len(ledige_senger_i_kupee)):
                            fortsett = False
                    else:
                        print("Vennligst svar med 1 eller 2.")

                for j in range(0, antall_senger):
                    fortsett = True
                    while fortsett:
                        pattern = r"\d+,\s*\d+"
                        valgt_seng = input("Oppgi seng på formen SengNr, VognNr: ")
                        if(re.match(pattern, valgt_seng)):
                            valgt_seng_tuple = tuple(map(int, valgt_seng.split(',')))
                            valgt_seng_str = f"({valgt_seng})"
                            if valgt_seng_tuple in sengArray[i][1:]:
                                print("Du har allerede valgt denne sengen!")
                            elif(valgt_seng_tuple in ledige_senger_i_kupee):
                                sengArray[i].append(valgt_seng_tuple)
                                print(f"Du valgte {valgt_seng_str}")
                                if(j != antall_senger - 1):
                                    print(f"Du har nå {antall_senger - 1 - j} seng(er) igjen å velge")
                                fortsett = False
                            else:
                                print("Ugyldig seng")
                        else:
                            print("Prøv på nytt")
    
    if any(len(sublist) > 1 for sublist in sengArray):
        kjopSengeBilletter(sengArray, dato, startstasjon, sluttstasjon)

#Sjekker hvem som eier den andre sengen i en kupee
def validerSengeBilletter(ledige_senger_i_kupee, opptatt_seng_av_kunde):
    andre_seng = None
    if not ledige_senger_i_kupee:
        print("Det er ingen ledige senger i denne kupeen.")
        return False
    elif len(ledige_senger_i_kupee) == 2:
        return True
    if len(ledige_senger_i_kupee) == 1:
        if ledige_senger_i_kupee[0][0] % 2 == 0:
            andre_seng = (ledige_senger_i_kupee[0][0] - 1, ledige_senger_i_kupee[0][1])
            for sengbillett in opptatt_seng_av_kunde:
                for seng_vogn in sengbillett:
                    if andre_seng == seng_vogn:
                        print("Du har allerede en sengbillett i kupeen, du kan kjøpe den andre sengen")
                        return True
            print('Du kan ikke kjøpe denne sengen, da noen andre allerede har kjøpt seng i denne kupeen')
            return False
        else:
            andre_seng = (ledige_senger_i_kupee[0][0] + 1, ledige_senger_i_kupee[0][1])
            for sengbillett in opptatt_seng_av_kunde:
                for seng_vogn in sengbillett[0:1]:
                    if andre_seng == seng_vogn:
                        print("Du har allerede en sengbillett på denne kupeen, du kan kjøpe den andre sengen")
                        return True
            print('Du kan ikke kjøpe denne sengen, noen andre har kjøpt i denne kupeen')
            return False
    


def kjopSengeBilletter(sengArray, dato, startstasjon, sluttstasjon):
    vognID = []
    for i,togrute in enumerate(sengArray):
        for j in range(1,len(togrute)):
            cursor.execute(f'''
            Select Vogn.VognID
                from Vogn 
                join VognITogruteforekomst on Vogn.VognID = VognITogruteforekomst.VognID
                join Togruteforekomst on VognITogruteforekomst.Rutenavn = Togruteforekomst.Rutenavn
                where Togruteforekomst.Rutenavn = '{sengArray[i][0]}' and Togruteforekomst.Dato ='{dato}'
                and VognITogruteforekomst.Nummer = '{togrute[j][1]}'
            ''')
            vognID.append(cursor.fetchone())
    VogntypeNavn = []
    for i in range(0, len(vognID)):
        cursor.execute(f'''
        Select Vogn.VogntypeNavn
            from Vogn
            where Vogn.VognID = '{vognID[i][0]}'
        ''')
        VogntypeNavn.append(cursor.fetchone())
    
    # Get the current date and time
    current_date = datetime.datetime.now().date()
    current_time = datetime.datetime.now().strftime('%H:%M')
    
    cursor.execute("SELECT MAX(Kundeordre.Ordrenummer) FROM Kundeordre")
    ordreNr = cursor.fetchone()
    if ordreNr[0] == None:
        ordreNr = 0
    else:
        ordreNr = ordreNr[0]


    table = PrettyTable()
    table.field_names = ["Sengenummer", "Vognnummer", "Startstasjon", "Sluttstasjon", "Togrute"]

    for i, togrute in enumerate(sengArray):
        for j in range(1,len(togrute)):
            ordreNr += 1
            cursor.execute("""
                INSERT INTO Kundeordre(Ordrenummer, Dato, Klokkeslett, KundeNr, Avgangsdato, Rutenavn)
                VALUES (?, ?, ?, ?, ?, ?)
                """, (ordreNr, current_date, current_time, kundeNr, dato, sengArray[i][0]))

            cursor.execute("SELECT MAX(SengBillett.BillettID) from SengBillett")
            billettID = cursor.fetchone()
            if billettID[0] == None:
                billettID = 0
            else: 
                billettID = billettID[0] + 1
            cursor.execute("""
                INSERT INTO SengBillett(BillettID, SengNr, VogntypeNavn, Ordrenummer, VognID, PåstigningsStasjon, AvstigningsStasjon)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (billettID,togrute[j][0],VogntypeNavn[0][0], ordreNr, vognID[0][0], startstasjon, sluttstasjon))
            table.add_row([togrute[j][0], togrute[j][1], startstasjon, sluttstasjon, sengArray[i][0]])    
            vognID.pop(0)
            VogntypeNavn.pop(0)

    print("Du bestilte følgende sengbilletter: ")
    print(table)


def kjopSeteBilletter(seteArray, dato, startstasjon, sluttstasjon):
    #Get vognID
    vognID = []
    for i,togrute in enumerate(seteArray):
        for j in range(1,len(togrute)):
            cursor.execute(f'''
            Select Vogn.VognID
                from Vogn 
                join VognITogruteforekomst on Vogn.VognID = VognITogruteforekomst.VognID
                join Togruteforekomst on VognITogruteforekomst.Rutenavn = Togruteforekomst.Rutenavn
                where Togruteforekomst.Rutenavn = '{seteArray[i][0]}' and Togruteforekomst.Dato ='{dato}'
                and VognITogruteforekomst.Nummer = '{togrute[j][1]}'
            ''')
            vognID.append(cursor.fetchone())
    
    
    VogntypeNavn = []
    for i in range(0, len(vognID)):
        cursor.execute(f'''
        Select Vogn.VogntypeNavn
            from Vogn
            where Vogn.VognID = '{vognID[i][0]}'
        ''')
        VogntypeNavn.append(cursor.fetchone())
    
    # Få dagens dato og tidspunkt
    current_date = datetime.datetime.now().date()
    current_time = datetime.datetime.now().strftime('%H:%M')

    cursor.execute("SELECT MAX(Kundeordre.Ordrenummer) FROM Kundeordre")
    ordreNr = cursor.fetchone()
    if ordreNr[0] == None:
        ordreNr = 0
    else:
        ordreNr = ordreNr[0]

    print("Du bestilte følgende setebilletter: ")
    table = PrettyTable()
    table.field_names = ["Setenummer", "Vognnummer", "Startstasjon", "Sluttstasjon", "Togrute"]

    for i, togrute in enumerate(seteArray):
        for j in range(1,len(togrute)):
            ordreNr += 1
            cursor.execute("""
                INSERT INTO Kundeordre(Ordrenummer, Dato, Klokkeslett, KundeNr, Avgangsdato, Rutenavn)
                VALUES (?, ?, ?, ?, ?, ?)
                """, (ordreNr, current_date, current_time, kundeNr, dato, seteArray[i][0]))

            cursor.execute("SELECT MAX(SeteBillett.BillettID) from SeteBillett")
            billettID = cursor.fetchone()
            if billettID[0] == None:
                billettID = 0
            else: 
                billettID = billettID[0] + 1
            cursor.execute("""
                INSERT INTO SeteBillett(BillettID, SeteNr, VogntypeNavn, Ordrenummer, VognID, PåstigningsStasjon, AvstigningsStasjon)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (billettID,togrute[j][0],VogntypeNavn[0][0], ordreNr, vognID[0][0], startstasjon, sluttstasjon))
        
            table.add_row([togrute[j][0], togrute[j][1], startstasjon, sluttstasjon, seteArray[i][0]])
            vognID.pop(0)
            VogntypeNavn.pop(0)

    print(table)

                    
# Sjekker at kunden allerede er registrert i kunderegisteret
kundeNr = input("Oppgi kundenummeret du er registrert med: ")
cursor.execute('SELECT Kunde.KundeNr FROM Kunde JOIN IKundeRegister ON Kunde.KundeNr = IKundeRegister.KundeNr WHERE IKundeRegister.KundeNr=?', (kundeNr))
result = cursor.fetchone()
while result is None:
    print("Dette kundenummeret er ikke i registeret vårt. Prøv igjen.")
    kundeNr = input("Oppgi kundenummeret du er registrert med: ")
    cursor.execute('SELECT Kunde.KundeNr FROM Kunde JOIN IKundeRegister ON Kunde.KundeNr = IKundeRegister.KundeNr WHERE IKundeRegister.KundeNr=?', (kundeNr))
    result = cursor.fetchone()

# Sjekker at ønsket startstasjon er en gyldig stasjon
startInput = input("Oppgi startstasjon (stor forbokstav): ")
cursor.execute('SELECT Navn FROM Jernbanestasjon WHERE Navn=?', (startInput,))
result = cursor.fetchone()
while result is None:
    print("Ugyldig startstasjon. Prøv igjen.")
    startInput = input("Oppgi startstasjon (stor forbokstav): ")
    cursor.execute('SELECT Navn FROM Jernbanestasjon WHERE Navn=?', (startInput,))
    result = cursor.fetchone()

# Sjekker at ønsket sluttstasjon er en gyldig stasjon
sluttInput = input("Oppgi sluttstasjon (stor forbokstav): ")
cursor.execute('SELECT Navn FROM Jernbanestasjon WHERE Navn=?', (sluttInput,))
result = cursor.fetchone()
while result is None:
    print("Ugyldig sluttstasjon. Prøv igjen.")
    sluttInput = input("Oppgi sluttstasjon (stor forbokstav): ")
    cursor.execute('SELECT Navn FROM Jernbanestasjon WHERE Navn=?', (sluttInput,))
    result = cursor.fetchone()

# Sjekker at ønsket dato for reisen er på riktig format
datoInput = input("Oppgi dato for reisen [YYYY-MM-DD]: ")
dateRegex = r'^\d{4}-\d{2}-\d{2}$'
while not re.fullmatch(dateRegex, datoInput):
    print("Ugyldig datoformat. Prøv igjen.")
    datoInput = input("Oppgi dato [YYYY-MM-DD]: ")

finn_ledige_billetter(datoInput,startInput,sluttInput)


con.commit()
con.close()