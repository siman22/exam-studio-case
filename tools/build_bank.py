"""
Builds js/bank.js from the question bank below.

Run from the repository root:   python tools/build_bank.py
It re-runs every SQL solution against the real databases and stops if an
answer in the bank no longer matches its query. The website itself never runs
this script; it only reads the generated js/bank.js.
"""
import json, os, sqlite3, sys, zipfile, tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# ---------------------------------------------------------------- answer rules
def num(v, tol=0, unit=""):          return {"type": "number", "value": v, "tol": tol, "unit": unit}
def pct(v, tol=0.0001):              return {"type": "percent", "value": v, "tol": tol}
def txt(*accept):                    return {"type": "text", "accept": list(accept)}
def dt(y, m, d, h=None, mi=None):    return {"type": "date", "value": [y, m, d, h, mi]}

# ---------------------------------------------------------------- datasets
DATASETS = {
    "nyc": {"name": "NYC film permits", "tool": "Excel",
            "files": ["excel/NYC_Film_Permits.csv", "excel/NYC_Film_Permits.xlsx"],
            "about": "33,502 film permits issued by New York City. The CSV is the raw export; the .xlsx is the same data already imported.",
            "source": "PwC Excel case"},
    "etl1": {"name": "Balance sheet extract", "tool": "Excel",
             "files": ["excel/ETL_Case1.csv"],
             "about": "A small, deliberately messy comma-separated extract of balance sheet items for seven companies.",
             "source": "ETL case 1"},
    "etl2": {"name": "Employee codes", "tool": "Excel",
             "files": ["excel/ETL_Case2.xlsx"],
             "about": "597 employees. EmployeeCode combines Location (3 letters), EmpID (4 digits), a hyphen, PlantID and PayPeriod (W or M), e.g. USA1234-12W.",
             "source": "ETL case 2"},
    "etl3": {"name": "Messy employee codes", "tool": "Excel",
             "files": ["excel/ETL_Case3.xlsx"],
             "about": "The same 597 employees with messier codes: locations have different lengths (US, Canada, Japan), EmpID has 1 to 3 digits and monthly pay is written as M or Mo.",
             "source": "ETL case 3"},
    "etl4": {"name": "Hotel journal entries", "tool": "Excel",
             "files": ["excel/ETL_Case4.xlsx"],
             "about": "789 journal entry lines from a hotel and conference center, plus lookup sheets: BusinessUnits, ChartOfAccounts, PreparerInfo and Source. PreparerID is only unique together with BusinessUnitID.",
             "source": "ETL case 4"},
    "integrateco": {"name": "IntegrateCo payroll", "tool": "Excel",
                    "files": ["excel/IntegrateCo_2015payroll.csv", "excel/IntegrateCo_2016payroll.csv",
                              "excel/IntegrateCo_jobcodes.csv", "excel/IntegrateCo_locations.csv"],
                    "about": "Pipe-delimited payroll for the first six months of 2015 (old system, one row per employee, pay date and job) and 2016 (new system, no dates). The three-digit job code sits inside Job/Project, e.g. 14S001SG contains job code 001.",
                    "source": "IntegrateCo case"},
    "restaurant": {"name": "Restaurant sales", "tool": "Excel",
                   "files": ["excel/Restaurant_data.xlsm"],
                   "about": "Daily sales per menu item for Larry's Commissary in 2018 (salesData), daily weather (weatherData) and football game days (gameData). Each sheet has a data dictionary. The workbook is macro-enabled; you can work with it without enabling macros.",
                   "source": "Regression case"},
    "chinook": {"name": "Chinook music store", "tool": "SQL",
                "files": ["sql/Chinook_Sqlite.sqlite"],
                "about": "A digital music store: Customer, Employee, Invoice, InvoiceLine, Track, Album, Artist, Genre, MediaType and playlists.",
                "source": "PwC SQL case"},
    "songs": {"name": "Spotify songs", "tool": "SQL",
              "files": ["sql/songs.db"],
              "about": "The 100 most streamed Spotify songs of 2018. Tables: songs and artists (songs.artist_id = artists.id).",
              "source": "CS50 songs"},
    "movies": {"name": "IMDb movies", "tool": "SQL",
               "files": ["sql/movies.db.zip"],
               "about": "IMDb data: movies, people, stars, directors and ratings. Unzip before opening (69 MB).",
               "source": "CS50 movies"},
    "fiftyville": {"name": "Fiftyville mystery", "tool": "SQL",
                   "files": ["sql/fiftyville.db"],
                   "about": "Town records around the theft of the CS50 duck on 28 July 2020 on Chamberlin Street: crime reports, interviews, security logs, ATM withdrawals, phone calls, flights and passengers.",
                   "source": "CS50 Fiftyville (optional case)"},
    "pcards": {"name": "OSU P-card transactions", "tool": "SQL",
               "files": ["sql/pcards.db.zip"],
               "about": "489,178 purchasing-card transactions of Oklahoma State University, 2010 to 2014, in one table called pcards. Year and Month come from TransactionDate. Negative amounts are returns. Unzip before opening (94 MB).",
               "source": "P-card case"},
}

# ---------------------------------------------------------------- questions
# Excel questions: "steps" is a worked approach. SQL questions: "sql" is a
# tested solution; "check" says how to compare its first result cell.
Q = []
def add(**kw): Q.append(kw)

# ===== NYC film permits (PwC Excel case; answers match the official key)
nyc_note = "Use the NYC film permits file."
add(id="E-01", case="nyc", topic="Import and inspect", level=1,
    prompt="Import the CSV into Excel. How many records (rows of data, excluding the header) does the table have?",
    answer=num(33502), steps=["Data > From Text/CSV, load to a table.", "Select any cell in the table; the status bar or `=ROWS(Table1)` gives the count."])
add(id="E-02", case="nyc", topic="Import and inspect", level=1,
    prompt="How many columns does the table have?",
    answer=num(14), steps=["`=COLUMNS(Table1)` or count the headers in row 1."])
add(id="E-03", case="nyc", topic="Data quality", level=1,
    prompt="How many records have a missing value for ZipCode?",
    answer=num(11), steps=["`=COUNTBLANK(Table1[ZipCode])`, or filter ZipCode on (Blanks)."])
add(id="E-04", case="nyc", topic="Data quality", level=2,
    prompt="A valid US zip code has exactly five digits. How many records have a ZipCode that is filled in but invalid?",
    answer=num(2),
    steps=["Add a helper column: `=IF([@ZipCode]=\"\",\"missing\",IF(LEN([@ZipCode])=5,\"ok\",\"invalid\"))`.",
           "Count the invalid rows with COUNTIF. Both invalid rows contain 83."])
add(id="E-05", case="nyc", topic="Data quality", level=1,
    prompt="Which column has the same value for every record? Give the exact column name.",
    answer=txt("EventAgency"),
    steps=["Put each column in a PivotTable row area, or use `=COUNTA(UNIQUE(Table1[EventAgency]))` for each column; only EventAgency returns 1."])
add(id="E-06", case="nyc", topic="Dates and times", level=1,
    prompt="What is the oldest EnteredOn value? Give the complete date and time.",
    answer=dt(2011, 12, 7, 16, 38), steps=["`=MIN(Table1[EnteredOn])` formatted as date and time."])
add(id="E-07", case="nyc", topic="Dates and times", level=1,
    prompt="What is the newest EnteredOn value? Give the complete date and time.",
    answer=dt(2018, 2, 9, 12, 46), steps=["`=MAX(Table1[EnteredOn])` formatted as date and time."])
add(id="E-08", case="nyc", topic="Pivot tables", level=1,
    prompt="How many different event types are there?",
    answer=num(4), steps=["`=COUNTA(UNIQUE(Table1[EventType]))`, or a PivotTable with EventType in rows."])
add(id="E-09", case="nyc", topic="Pivot tables", level=1,
    prompt="What is the most common event type?",
    answer=txt("Shooting Permit"), steps=["PivotTable: EventType in rows, Count of EventID in values, sort descending."])
add(id="E-10", case="nyc", topic="Pivot tables", level=1,
    prompt="Consider only shooting permits. What is the most common Category?",
    answer=txt("Television"), steps=["PivotTable filtered on EventType = Shooting Permit, Category in rows, count, sort descending."])
add(id="E-11", case="nyc", topic="Pivot tables", level=1,
    prompt="Consider only shooting permits. How many were granted for student films (Category = Student)?",
    answer=num(193), steps=["`=COUNTIFS(Table1[EventType],\"Shooting Permit\",Table1[Category],\"Student\")`"])
add(id="E-12", case="nyc", topic="Text functions", level=2,
    prompt="Consider only shooting permits. What percentage required approval by more than one Community Board? Give the percentage with two decimals.",
    answer=pct(0.0784, 0.0001),
    steps=["Several boards are listed in CommunityBoard(s) separated by commas.",
           "Helper column: `=ISNUMBER(SEARCH(\",\",[@[CommunityBoard(s)]]))`.",
           "Share of TRUE among shooting permits: 2,249 / 28,680 = 7.84%."])
add(id="E-13", case="nyc", topic="Pivot tables", level=2,
    prompt="Consider only shooting permits and use the year of StartDateTime. In which year did the number of shoots in Brooklyn first outnumber the shoots in Manhattan?",
    answer=num(2017),
    steps=["Helper column `=YEAR([@StartDateTime])`.", "PivotTable: year in rows, Borough in columns, count. Brooklyn 1,719 vs Manhattan 1,550 in 2017."])
add(id="E-14", case="nyc", topic="Text functions", level=2,
    prompt="Consider only shooting permits in Manhattan. What percentage take place on or near Broadway (ParkingHeld mentions BROADWAY)? Round to the nearest whole percent.",
    answer=pct(0.20, 0.005),
    steps=["Helper column `=ISNUMBER(SEARCH(\"BROADWAY\",[@ParkingHeld]))`.", "Share of TRUE among Manhattan shooting permits = 20%."])
add(id="E-15", case="nyc", topic="Dates and times", level=2,
    prompt="Consider only shooting permits. How many shooting permit applications entered in 2013 or later came from a foreign country (Country is not United States of America)?",
    answer=num(7), steps=["`=COUNTIFS(Table1[EventType],\"Shooting Permit\",Table1[EnteredOn],\">=\"&DATE(2013,1,1),Table1[Country],\"<>United States of America\")`",
                          "United Kingdom 4, Panama 2, Canada 1."])
add(id="E-16", case="nyc", topic="Dates and times", level=2,
    prompt="Consider only shooting permits. What is the average duration (EndDateTime minus StartDateTime) in hours, rounded to the nearest half hour?",
    answer=num(17, 0.01, "hours"),
    steps=["Helper column `=([@EndDateTime]-[@StartDateTime])*24`. Excel stores dates as days, so multiply by 24.", "Average is 16.98 hours, which rounds to 17."])
add(id="E-17", case="nyc", topic="Dates and times", level=2,
    prompt="Consider only shooting permits. What was the duration of the shortest shoot, in minutes?",
    answer=num(1, 0, "minutes"), steps=["Duration in minutes: `=([@EndDateTime]-[@StartDateTime])*24*60`, then MIN."])
add(id="E-18", case="nyc", topic="Dates and times", level=2,
    prompt="Consider only shooting permits. What is the average lead time in days between EnteredOn and StartDateTime? Round to the nearest day.",
    answer=num(5, 0, "days"), steps=["Helper column `=[@StartDateTime]-[@EnteredOn]`, then AVERAGE (4.59 days, rounded to 5)."])
add(id="E-19", case="nyc", topic="Dates and times", level=2,
    prompt="Consider only shooting permits. On which day of the week do shoots most often start? Give the full day name.",
    answer=txt("Thursday", "torsdag"), steps=["Helper column `=TEXT([@StartDateTime],\"dddd\")`, then a PivotTable count."])
add(id="E-20", case="nyc", topic="Dates and times", level=3,
    prompt="Consider only shooting permits. What percentage include shooting on at least part of a Friday (any calendar day from the start date to the end date is a Friday)? Give the percentage with two decimals.",
    answer=pct(0.2365, 0.0001),
    steps=["For each permit, list the weekdays between INT(start) and INT(end). One formula: `=SUMPRODUCT(--(WEEKDAY(ROW(INDIRECT(INT([@StartDateTime])&\":\"&INT([@EndDateTime]))),2)=5))>0`.",
           "Share of TRUE = 23.65%."])

# ===== ETL case 1
add(id="E-21", case="etl1", topic="Duplicates", level=1,
    prompt="Open the file. How many data rows (excluding the header) remain after removing rows that are exact duplicates of another row?",
    answer=num(21), steps=["Data > Remove Duplicates on all columns removes the repeated Aptevo 2018 row: 22 rows become 21."])
add(id="E-22", case="etl1", topic="Delimiters", level=1,
    prompt="One company's rows split into too many columns when the CSV is opened, because its name contains a comma without a text qualifier. Which company is it?",
    answer=txt("Apple", "Apple, Inc.", "Apple Inc.", "Apple Inc", "AAPL"),
    steps=["Open the file in a text editor: `AAPL,Apple, Inc.,2016,...` has no quotes around the name, so the comma is read as a delimiter."])
add(id="E-23", case="etl1", topic="Units", level=2,
    prompt="Cash is recorded in mixed units (some values end in M or K). What is Apple's 2018 cash in whole dollars?",
    answer=num(25900000000, 0, "USD"),
    steps=["\"25900 M\" means 25,900 million.", "Formula idea: `=IF(RIGHT(A2)=\"M\",VALUE(LEFT(A2,LEN(A2)-2))*10^6,IF(RIGHT(A2)=\"K\",VALUE(LEFT(A2,LEN(A2)-2))*10^3,VALUE(A2)))`."])
add(id="E-24", case="etl1", topic="Unique identifiers", level=1,
    prompt="Amazon's ticker is not written consistently. How many different spellings of Amazon's ticker appear in the file?",
    answer=num(3), steps=["AMZN, A M Z N and AM ZN. `SUBSTITUTE(A2,\" \",\"\")` makes them identical."])
add(id="E-25", case="etl1", topic="Units", level=2,
    prompt="After removing the duplicate row and converting K values to whole dollars, what is Aptevo Therapeutics' total cash across 2016 to 2018?",
    answer=num(47400000, 0, "USD"), steps=["9,700 K + 7,100 K + 30,600 K = 47,400,000. Without removing the duplicate you would get 78,000,000."])
add(id="E-26", case="etl1", topic="Unique identifiers", level=1,
    prompt="Which company has no ticker at all?",
    answer=txt("Armada Hoffler", "Armada Hoffler Properties", "Armada Hoffler Properties Inc.", "Armada Hoffler Properties Inc"),
    steps=["Filter Ticker on (Blanks)."])

# ===== ETL case 2
etl2_setup = "Split EmployeeCode into Location, EmpID, PlantID and PayPeriod, and build LocationPlantID as Location-PlantID (e.g. USA-12)."
add(id="E-27", case="etl2", topic="Text extraction", level=2, setup=etl2_setup,
    prompt="How many distinct LocationPlantID values are there?",
    answer=num(133),
    steps=["Location `=LEFT(A2,3)`, EmpID `=MID(A2,4,4)`, PlantID `=MID(A2,FIND(\"-\",A2)+1,LEN(A2)-FIND(\"-\",A2)-1)`, PayPeriod `=RIGHT(A2,1)`.",
           "LocationPlantID `=D2&\"-\"&F2`, then `=COUNTA(UNIQUE(H2:H598))`."])
add(id="E-28", case="etl2", topic="Text extraction", level=1, setup=etl2_setup,
    prompt="How many employees work at USA-12?",
    answer=num(10), steps=["`=COUNTIF(H2:H598,\"USA-12\")`"])
add(id="E-29", case="etl2", topic="Text extraction", level=1, setup=etl2_setup,
    prompt="How many employees in Germany (GER) are paid weekly?",
    answer=num(29), steps=["`=COUNTIFS(D2:D598,\"GER\",G2:G598,\"W\")`"])
add(id="E-30", case="etl2", topic="Text extraction", level=2, setup=etl2_setup,
    prompt="Which LocationPlantID has the highest plant number in the company?",
    answer=txt("MEX-26"), steps=["Convert PlantID with VALUE, then MAX = 26, which occurs only in Mexico."])
add(id="E-31", case="etl2", topic="Text extraction", level=1, setup=etl2_setup,
    prompt="How many employees are paid monthly?",
    answer=num(339), steps=["`=COUNTIF(G2:G598,\"M\")`"])

# ===== ETL case 3
etl3_setup = "Extract Location, EmpID, PlantID and PayPeriod with formulas. Locations vary in length (US, Canada, Japan, ...), EmpID has 1 to 3 digits, and M and Mo both mean monthly."
add(id="E-32", case="etl3", topic="Text extraction", level=3, setup=etl3_setup,
    prompt="Build LocationPlantID as Location-PlantID (e.g. US-1). How many distinct LocationPlantID values are there?",
    answer=num(133),
    steps=["First digit position: `=MIN(FIND({0,1,2,3,4,5,6,7,8,9},A2&\"0123456789\"))`.",
           "Location `=LEFT(A2,pos-1)`; EmpID `=MID(A2,pos,FIND(\"-\",A2)-pos)`.",
           "PlantID: the digits after the hyphen; PayPeriod: the letters after them.", "Count unique LocationPlantID values: 133."])
add(id="E-33", case="etl3", topic="Text extraction", level=2, setup=etl3_setup,
    prompt="How many employees in Japan are paid monthly (M or Mo)?",
    answer=num(51), steps=["Standardise PayPeriod with `=LEFT(pay,1)`, then COUNTIFS on Location = Japan and M."])
add(id="E-34", case="etl3", topic="Text extraction", level=1, setup=etl3_setup,
    prompt="How many employee codes record the pay period as Mo (rather than M)?",
    answer=num(181), steps=["`=COUNTIF(A2:A598,\"*Mo\")`. Of the 339 monthly employees, 181 use Mo and 158 use M."])
add(id="E-35", case="etl3", topic="Text extraction", level=2, setup=etl3_setup,
    prompt="How many employees work at plant 1 in the United States (LocationPlantID US-1)?",
    answer=num(6), steps=["COUNTIF on LocationPlantID = US-1. Watch out: a text-based match on \"US-1\" must not also count US-10, US-11, and so on."])
add(id="E-36", case="etl3", topic="Text extraction", level=3, setup=etl3_setup,
    prompt="Convert EmpID to a number. What is the sum of all EmpID values? (A good check that every extraction worked.)",
    answer=num(178503), steps=["`=SUM(VALUE(E2:E598))`. If any row was extracted wrongly, the sum will differ."])

# ===== ETL case 4
etl4_setup = "Join JELineItems to the lookup sheets. Preparers are identified by the combination of PreparerID and BusinessUnitID."
add(id="E-37", case="etl4", topic="Lookups and joins", level=3, setup=etl4_setup,
    prompt="When you look up the preparer using both PreparerID and BusinessUnitID, how many journal entry lines find no matching preparer?",
    answer=num(148),
    steps=["`=IFERROR(INDEX(PreparerInfo!A:A,MATCH(1,(PreparerInfo!B:B=D2)*(PreparerInfo!C:C=C2),0)),\"no match\")` (array formula, or use XLOOKUP with two conditions).",
           "Count \"no match\": 148. Looking up on PreparerID alone would wrongly return a name for every line."])
add(id="E-38", case="etl4", topic="Lookups and joins", level=2, setup=etl4_setup,
    prompt="Which preparer (name only, without job title) is on the most journal entry lines?",
    answer=txt("Carolyn Slater"),
    steps=["PreparerName holds Name|Title. Take the name with `=TRIM(LEFT(name,FIND(\"|\",name)-1))`.", "PivotTable count: Carolyn Slater has 182 lines."])
add(id="E-39", case="etl4", topic="Lookups and joins", level=1, setup=etl4_setup,
    prompt="How many journal entry lines have the source PURCHASE CARD?",
    answer=num(152), steps=["`=XLOOKUP(E2,Source!A:A,Source!B:B)` then COUNTIF."])
add(id="E-40", case="etl4", topic="Lookups and joins", level=2, setup=etl4_setup,
    prompt="What is the total Amount of all lines whose AccountClass is Payroll Expense?",
    answer=num(234417.28, 0.01, "USD"), steps=["Look up AccountClass from ChartOfAccounts via GLAccountNumber, then SUMIF."])
add(id="E-41", case="etl4", topic="Lookups and joins", level=2, setup=etl4_setup,
    prompt="What is the sum of Amount for all lines whose AccountType is Revenue? Keep the sign.",
    answer=num(-398321.61, 0.01, "USD"),
    steps=["Revenue is mostly credits, so the sum is negative: -398,321.61."])
add(id="E-42", case="etl4", topic="Lookups and joins", level=1, setup=etl4_setup,
    prompt="How many journal entry lines belong to the FOOD SERVICE business unit?",
    answer=num(423), steps=["Look up BusinessUnit from BusinessUnits via BusinessUnitID, then COUNTIF."])
add(id="E-43", case="etl4", topic="Completeness checks", level=1,
    prompt="What is the total of the Debit column? (As a completeness check, the Amount column should sum to zero.)",
    answer=num(1130428.13, 0.01, "USD"), steps=["`=SUM(JELineItems!H:H)`. Credits sum to -1,130,428.13, so total Amount is 0."])

# ===== IntegrateCo
ic_setup = "Import the pipe-delimited files. Extract the three-digit job code from Job (2015) and Project (2016): skip the two-digit year and the optional H or S, then take three digits. Gross pay in 2015 is Reg_Pay + OT_Pay."
add(id="E-44", case="integrateco", topic="Aggregation", level=1, setup=ic_setup,
    prompt="What were total gross wages (Reg_Pay + OT_Pay) in the first six months of 2015?",
    answer=num(1086734.19, 0.01, "USD"), steps=["Helper column `=[@Reg_Pay]+[@OT_Pay]`, then SUM."])
add(id="E-45", case="integrateco", topic="Aggregation", level=1, setup=ic_setup,
    prompt="What were total gross wages in the first six months of 2016?",
    answer=num(1352789.75, 0.01, "USD"), steps=["`=SUM(Gross_Wages)` in the 2016 data."])
add(id="E-46", case="integrateco", topic="Aggregation", level=1, setup=ic_setup,
    prompt="By how much did gross wages increase from 2015 to 2016 (2016 minus 2015)?",
    answer=num(266055.56, 0.01, "USD"), steps=["1,352,789.75 - 1,086,734.19 = 266,055.56: the roughly $266,000 the CFO noticed."])
add(id="E-47", case="integrateco", topic="Data quality", level=2, setup=ic_setup,
    prompt="Valid job codes are 001 to 012. Which invalid job code appears in the 2015 data?",
    answer=txt("144"),
    steps=["Job code `=MID([@Job],IF(ISNUMBER(VALUE(MID([@Job],3,1))),3,4),3)`.", "Compare against the jobcodes table with COUNTIF; 144 has no match."])
add(id="E-48", case="integrateco", topic="Comparison across years", level=3, setup=ic_setup,
    prompt="Among job codes that have gross wages in both years, which job code had the largest increase in gross wages from 2015 to 2016?",
    answer=txt("006", "6"),
    steps=["PivotTables of gross wages by job code for each year, combined with XLOOKUP.",
           "009, 010, 011 and 012 only exist in 2016, so they are excluded. 006 (Service) rose by 23,128.33."])
add(id="E-49", case="integrateco", topic="Data quality", level=1, setup=ic_setup,
    prompt="How many 2016 rows have no employee number (\"phantom\" entries)?",
    answer=num(68), steps=["`=COUNTBLANK(Employee_Number column)`"])
add(id="E-50", case="integrateco", topic="Data quality", level=1, setup=ic_setup,
    prompt="What is the total gross wage amount of the 2016 phantom entries?",
    answer=num(32951.29, 0.01, "USD"), steps=["`=SUMIFS(Gross_Wages,Employee_Number,\"\")`"])
add(id="E-51", case="integrateco", topic="Aggregation", level=1, setup=ic_setup,
    prompt="Which employee earned the most overtime pay in 2015, and how much? Enter the amount.",
    answer=num(4186.24, 0.01, "USD"), steps=["PivotTable: Emp_No and name in rows, sum of OT_Pay, sorted descending. Cindy Lunt: 4,186.24 for 91.5 OT hours."])
add(id="E-52", case="integrateco", topic="Aggregation", level=2, setup=ic_setup,
    prompt="Which job code had the most overtime pay in 2015?",
    answer=txt("006", "6"), steps=["PivotTable on the extracted job code, sum of OT_Pay. 006 (Service): 6,007.52."])
add(id="E-53", case="integrateco", topic="Aggregation", level=1, setup=ic_setup,
    prompt="What was the total employee cost in 2016 (gross wages + SocSec_Medicare + FUTA + SUTA + Work_Comp)?",
    answer=num(1486454.83, 0.01, "USD"), steps=["Sum the five columns over all 2016 rows, including phantom entries."])
add(id="E-54", case="integrateco", topic="Controls testing", level=3, setup=ic_setup,
    prompt="Treat all 2015 pay on the same Pay_Date as one pay period. How many employee and pay-date combinations show overtime hours even though the employee worked fewer than 40 regular hours?",
    answer=num(103),
    steps=["PivotTable: employee name and Pay_Date in rows, sum of Reg_Hrs and OT_Hrs.", "Filter: Reg_Hrs < 40 and OT_Hrs > 0. 103 combinations; Cindy Lunt appears often."])
add(id="E-55", case="integrateco", topic="Dates and times", level=2, setup=ic_setup,
    prompt="Group 2015 gross wages by month of Pay_Date. By how much does the highest month exceed the six-month average?",
    answer=num(40394.81, 0.01, "USD"), steps=["`=MONTH([@Pay_Date])`, PivotTable by month, average = 181,122.37.", "May: 221,517.17 - 181,122.37 = 40,394.81."])
add(id="E-56", case="integrateco", topic="Lookups and joins", level=3, setup=ic_setup,
    prompt="Join the locations file on employee name and exclude phantom entries. What was the average pay per hour (gross wages / (regular + overtime hours)) at location 2 in 2016? Round to two decimals.",
    answer=num(35.65, 0.01, "USD per hour"),
    steps=["Build FirstName LastName for 2015; 2016 already has Employee_Name. XLOOKUP the location.",
           "Location 2, 2016: 768,848.06 / 21,567.25 = 35.65 (location 1: 30.84)."])

# ===== Restaurant regression (Excel)
rs_setup = "Aggregate salesData to one row per date (sum netTotal and the lagged netTotal columns), then merge weatherData and gameData by date. Days without a game get gameDay = 0."
add(id="E-57", case="restaurant", topic="Aggregation", level=1,
    prompt="What were the restaurant's total net sales (sum of netTotal) in 2018?",
    answer=num(1014289, 0, "USD"), steps=["`=SUM(salesData[netTotal])`"])
add(id="E-58", case="restaurant", topic="Aggregation", level=1, setup=rs_setup,
    prompt="After aggregating salesData to one row per date, how many dates are there?",
    answer=num(312), steps=["`=COUNTA(UNIQUE(salesData[date]))`, or a PivotTable with date in rows."])
add(id="E-59", case="restaurant", topic="Aggregation", level=1, setup=rs_setup,
    prompt="On which date were total daily net sales highest?",
    answer=dt(2018, 4, 27), steps=["PivotTable by date, sum of netTotal, sort descending: 27 April 2018 with 7,033."])
add(id="E-60", case="restaurant", topic="Regression", level=3, setup=rs_setup,
    prompt="Regress total daily netTotal on total daily netTotal_7 (Data Analysis > Regression). Using the last date's total sales as the input, what are predicted sales 7 days after the last date? Round to two decimals.",
    answer=num(3264.33, 1.0, "USD"),
    steps=["Coefficients: intercept 1,359.16, netTotal_7 0.5858 (R² 0.378).", "Last date 31 Dec 2018 has sales 3,252, so the prediction is 1,359.16 + 0.5858 × 3,252 = 3,264.33."])
add(id="E-61", case="restaurant", topic="Regression", level=2, setup=rs_setup,
    prompt="Regress total daily netTotal on tmax (maximum temperature). What is the coefficient on tmax? Round to two decimals.",
    answer=num(7.58, 0.01), steps=["Each extra degree Fahrenheit is associated with about $7.58 more daily sales (p = 0.008, R² = 0.023): significant, but temperature explains little of the variation."])
add(id="E-62", case="restaurant", topic="Regression", level=2, setup=rs_setup,
    prompt="Regress total daily netTotal on gameDay. What is the coefficient on gameDay? Round to two decimals.",
    answer=num(1436.30, 0.05), steps=["Game days have about $1,436 higher sales than other days (intercept 3,191.08, p < 0.001)."])
add(id="E-63", case="restaurant", topic="Regression", level=3, setup=rs_setup,
    prompt="Create gameDay × netTotal_364 and regress total daily netTotal on netTotal_364, gameDay and the interaction. What is the R Square? Round to three decimals.",
    answer=num(0.536, 0.001),
    steps=["Interaction column: `=gameDay*netTotal_364`.", "R² = 0.536. Neither gameDay (p = 0.63) nor the interaction (p = 0.95) is significant once last year's sales are included."])

# ===== Chinook (PwC SQL case)
add(id="S-01", case="chinook", topic="Table structure", level=1,
    prompt="How many columns does the Customer table have?",
    answer=num(13), sql="SELECT COUNT(*) FROM pragma_table_info('Customer');", check=True)
add(id="S-02", case="chinook", topic="SELECT and LIMIT", level=1,
    prompt="Select only the first 5 rows of Customer (in stored order). What is the Country in the last of these rows?",
    answer=txt("Czech Republic"), sql="SELECT Country\nFROM Customer\nLIMIT 1 OFFSET 4;", check=True)
add(id="S-03", case="chinook", topic="ORDER BY", level=1,
    prompt="Sort Customer by LastName (A to Z). What is the last name in the third row?",
    answer=txt("Bernard"), sql="SELECT LastName\nFROM Customer\nORDER BY LastName\nLIMIT 1 OFFSET 2;", check=True)
add(id="S-04", case="chinook", topic="COUNT", level=1,
    prompt="How many rows are in the Invoice table?",
    answer=num(412), sql="SELECT COUNT(*) FROM Invoice;", check=True)
add(id="S-05", case="chinook", topic="WHERE", level=1,
    prompt="How many invoices have a Total greater than $20?",
    answer=num(4), sql="SELECT COUNT(*)\nFROM Invoice\nWHERE Total > 20;", check=True)
add(id="S-06", case="chinook", topic="WHERE", level=1,
    prompt="How many invoices have a Total greater than $10 and less than $20?",
    answer=num(60), sql="SELECT COUNT(*)\nFROM Invoice\nWHERE Total > 10 AND Total < 20;", check=True)
add(id="S-07", case="chinook", topic="IN", level=1,
    prompt="How many invoices have a BillingCountry of Brazil, Argentina or Chile?",
    answer=num(49), sql="SELECT COUNT(*)\nFROM Invoice\nWHERE BillingCountry IN ('Brazil', 'Argentina', 'Chile');", check=True)
add(id="S-08", case="chinook", topic="LIKE", level=1,
    prompt="How many invoices have a BillingCountry that starts with C?",
    answer=num(77), sql="SELECT COUNT(*)\nFROM Invoice\nWHERE BillingCountry LIKE 'C%';", check=True)
add(id="S-09", case="chinook", topic="NULL", level=1,
    prompt="How many customers list their company?",
    answer=num(10), sql="SELECT COUNT(*)\nFROM Customer\nWHERE Company IS NOT NULL;", check=True)
add(id="S-10", case="chinook", topic="COUNT", level=1,
    prompt="How many employees does Chinook have?",
    answer=num(8), sql="SELECT COUNT(*) FROM Employee;", check=True)
add(id="S-11", case="chinook", topic="String functions", level=1,
    prompt="How many characters long is the longest LastName in the Employee table?",
    answer=num(8), sql="SELECT MAX(LENGTH(LastName))\nFROM Employee;", check=True)
add(id="S-12", case="chinook", topic="Date functions", level=2,
    prompt="How many employees were born on a Sunday?",
    answer=num(2), sql="SELECT COUNT(*)\nFROM Employee\nWHERE strftime('%w', BirthDate) = '0';  -- 0 = Sunday", check=True)
add(id="S-13", case="chinook", topic="Date functions", level=2,
    prompt="How old, in years, was the oldest employee when they were hired? Round to one decimal.",
    answer=num(55.6, 0.15, "years"),
    sql="SELECT MAX((julianday(HireDate) - julianday(BirthDate)) / 365.25)\nFROM Employee;", check=True)
add(id="S-14", case="chinook", topic="GROUP BY", level=2,
    prompt="Rank billing countries by the total value of their invoices. What is the total for the top country?",
    answer=num(523.06, 0.01, "USD"),
    sql="SELECT BillingCountry, ROUND(SUM(Total), 2) AS TotalValue\nFROM Invoice\nGROUP BY BillingCountry\nORDER BY TotalValue DESC;", check="col2")
add(id="S-15", case="chinook", topic="COUNT", level=1,
    prompt="How many invoice line items are there?",
    answer=num(2240), sql="SELECT COUNT(*) FROM InvoiceLine;", check=True)
add(id="S-16", case="chinook", topic="DISTINCT", level=1,
    prompt="How many distinct unit prices appear in InvoiceLine?",
    answer=num(2), sql="SELECT COUNT(DISTINCT UnitPrice)\nFROM InvoiceLine;", check=True)
add(id="S-17", case="chinook", topic="GROUP BY", level=2,
    prompt="How many downloads (sum of Quantity) were made at the price of 0.99?",
    answer=num(2129), sql="SELECT SUM(Quantity)\nFROM InvoiceLine\nWHERE UnitPrice = 0.99;", check=True)
add(id="S-18", case="chinook", topic="Subqueries", level=2,
    prompt="No track has been downloaded more than twice. How many tracks have been downloaded exactly twice?",
    answer=num(256),
    sql="SELECT COUNT(*)\nFROM (\n  SELECT TrackId, SUM(Quantity) AS Downloads\n  FROM InvoiceLine\n  GROUP BY TrackId\n  HAVING Downloads = 2\n);", check=True)
add(id="S-19", case="chinook", topic="Date functions", level=1,
    prompt="What is the date of the most recent invoice?",
    answer=dt(2013, 12, 22), sql="SELECT MAX(InvoiceDate) FROM Invoice;", check=False)
add(id="S-20", case="chinook", topic="JOIN", level=2,
    prompt="What is the most popular genre, measured by number of invoice lines?",
    answer=txt("Rock"),
    sql="SELECT g.Name, COUNT(*) AS Sold\nFROM InvoiceLine il\nJOIN Track t ON t.TrackId = il.TrackId\nJOIN Genre g ON g.GenreId = t.GenreId\nGROUP BY g.Name\nORDER BY Sold DESC;", check=True)
add(id="S-21", case="chinook", topic="JOIN", level=2,
    prompt="How many distinct albums have had at least one of their tracks downloaded?",
    answer=num(304),
    sql="SELECT COUNT(DISTINCT t.AlbumId)\nFROM InvoiceLine il\nJOIN Track t ON t.TrackId = il.TrackId;", check=True)
add(id="S-22", case="chinook", topic="JOIN", level=3,
    prompt="Each customer has a support representative (SupportRepId). Which employee's customers generated the highest total invoice value? Give the full name.",
    answer=txt("Jane Peacock"),
    sql="SELECT e.FirstName || ' ' || e.LastName AS Rep, ROUND(SUM(i.Total), 2) AS Sales\nFROM Invoice i\nJOIN Customer c ON c.CustomerId = i.CustomerId\nJOIN Employee e ON e.EmployeeId = c.SupportRepId\nGROUP BY e.EmployeeId\nORDER BY Sales DESC;", check=True)
add(id="S-23", case="chinook", topic="JOIN", level=3,
    prompt="Which artist has sold the most tracks (number of invoice lines)?",
    answer=txt("Iron Maiden"),
    sql="SELECT ar.Name, COUNT(*) AS Sold\nFROM InvoiceLine il\nJOIN Track t ON t.TrackId = il.TrackId\nJOIN Album al ON al.AlbumId = t.AlbumId\nJOIN Artist ar ON ar.ArtistId = al.ArtistId\nGROUP BY ar.ArtistId\nORDER BY Sold DESC;", check=True)
add(id="S-24", case="chinook", topic="Subqueries", level=2,
    prompt="How many tracks have never been sold?",
    answer=num(1519),
    sql="SELECT COUNT(*)\nFROM Track\nWHERE TrackId NOT IN (SELECT TrackId FROM InvoiceLine);", check=True)

# ===== Songs
add(id="S-25", case="songs", topic="ORDER BY", level=1,
    prompt="Which song has the highest energy?",
    answer=txt("Nice For What"), sql="SELECT name, energy\nFROM songs\nORDER BY energy DESC\nLIMIT 1;", check=True)
add(id="S-26", case="songs", topic="ORDER BY", level=1,
    prompt="List songs in decreasing order of tempo. Which song comes first?",
    answer=txt("Corazon (feat. Nego do Borel)", "Corazon"), sql="SELECT name\nFROM songs\nORDER BY tempo DESC\nLIMIT 1;", check=True)
add(id="S-27", case="songs", topic="ORDER BY", level=1,
    prompt="Which song is the third longest?",
    answer=txt("Walk It Talk It"), sql="SELECT name\nFROM songs\nORDER BY duration_ms DESC\nLIMIT 1 OFFSET 2;", check=True)
add(id="S-28", case="songs", topic="WHERE", level=1,
    prompt="How many songs have danceability, energy and valence all greater than 0.6?",
    answer=num(23), sql="SELECT COUNT(*)\nFROM songs\nWHERE danceability > 0.6 AND energy > 0.6 AND valence > 0.6;", check=True)
add(id="S-29", case="songs", topic="Aggregate functions", level=1,
    prompt="What is the average tempo of all songs? Round to two decimals.",
    answer=num(119.90, 0.01), sql="SELECT ROUND(AVG(tempo), 2) FROM songs;", check=True)
add(id="S-30", case="songs", topic="Subqueries", level=1,
    prompt="How many songs are by Drake? Do not assume Drake's artist_id.",
    answer=num(4), sql="SELECT COUNT(*)\nFROM songs\nWHERE artist_id = (SELECT id FROM artists WHERE name = 'Drake');", check=True)
add(id="S-31", case="songs", topic="JOIN", level=2,
    prompt="What is the average energy of songs by Post Malone? Round to four decimals.",
    answer=num(0.6088, 0.0001),
    sql="SELECT ROUND(AVG(s.energy), 4)\nFROM songs s\nJOIN artists a ON a.id = s.artist_id\nWHERE a.name = 'Post Malone';", check=True)
add(id="S-32", case="songs", topic="LIKE", level=1,
    prompt="Songs that feature other artists include \"feat.\" in the name. How many such songs are there?",
    answer=num(18), sql="SELECT COUNT(*)\nFROM songs\nWHERE name LIKE '%feat.%';", check=True)

# ===== Movies
add(id="S-33", case="movies", topic="WHERE", level=1,
    prompt="How many movies were released in 2007?",
    answer=num(8214), sql="SELECT COUNT(*)\nFROM movies\nWHERE year = 2007;", check=True)
add(id="S-34", case="movies", topic="WHERE", level=1,
    prompt="In which year was Johnny Depp born?",
    answer=num(1963), sql="SELECT birth\nFROM people\nWHERE name = 'Johnny Depp';", check=True)
add(id="S-35", case="movies", topic="WHERE", level=1,
    prompt="How many movies have a release year of 2017 or later (including future years)?",
    answer=num(68236), sql="SELECT COUNT(*)\nFROM movies\nWHERE year >= 2017;", check=True)
add(id="S-36", case="movies", topic="WHERE", level=1,
    prompt="How many movies have an IMDb rating greater than 9.0?",
    answer=num(1297), sql="SELECT COUNT(*)\nFROM ratings\nWHERE rating > 9.0;", check=True)
add(id="S-37", case="movies", topic="LIKE", level=1,
    prompt="Assume every movie whose title begins with \"Toy Story\" is a Toy Story movie. How many are there?",
    answer=num(5), sql="SELECT COUNT(*)\nFROM movies\nWHERE title LIKE 'Toy Story%';", check=True)
add(id="S-38", case="movies", topic="JOIN", level=2,
    prompt="What is the average rating of all movies released in 2013? Round to three decimals.",
    answer=num(6.234, 0.001),
    sql="SELECT ROUND(AVG(r.rating), 3)\nFROM ratings r\nJOIN movies m ON m.id = r.movie_id\nWHERE m.year = 2013;", check=True)
add(id="S-39", case="movies", topic="JOIN", level=2,
    prompt="List all movies released in 2011 that have a rating. How many are there?",
    answer=num(7437),
    sql="SELECT COUNT(*)\nFROM movies m\nJOIN ratings r ON r.movie_id = m.id\nWHERE m.year = 2011;", check=True)
add(id="S-40", case="movies", topic="JOIN", level=2,
    prompt="How many people starred in Harry Potter and the Sorcerer's Stone?",
    answer=num(4),
    sql="SELECT COUNT(*)\nFROM stars st\nJOIN movies m ON m.id = st.movie_id\nWHERE m.title = 'Harry Potter and the Sorcerer''s Stone';", check=True)
add(id="S-41", case="movies", topic="DISTINCT", level=2,
    prompt="How many different people starred in at least one movie released in 2003? Count each person once.",
    answer=num(16368),
    sql="SELECT COUNT(DISTINCT st.person_id)\nFROM stars st\nJOIN movies m ON m.id = st.movie_id\nWHERE m.year = 2003;", check=True)
add(id="S-42", case="movies", topic="DISTINCT", level=2,
    prompt="How many different people have directed a movie with a rating of at least 8.0?",
    answer=num(14058),
    sql="SELECT COUNT(DISTINCT d.person_id)\nFROM directors d\nJOIN ratings r ON r.movie_id = d.movie_id\nWHERE r.rating >= 8.0;", check=True)
add(id="S-43", case="movies", topic="JOIN", level=2,
    prompt="What is the highest rating among movies Helena Bonham Carter starred in?",
    answer=num(8.0, 0.001),
    sql="SELECT MAX(r.rating)\nFROM stars st\nJOIN people p ON p.id = st.person_id\nJOIN ratings r ON r.movie_id = st.movie_id\nWHERE p.name = 'Helena Bonham Carter';", check=True)
add(id="S-44", case="movies", topic="Subqueries", level=3,
    prompt="In how many movies did both Johnny Depp and Helena Bonham Carter star?",
    answer=num(6),
    sql="SELECT COUNT(*)\nFROM movies\nWHERE id IN (SELECT movie_id FROM stars WHERE person_id =\n             (SELECT id FROM people WHERE name = 'Johnny Depp'))\n  AND id IN (SELECT movie_id FROM stars WHERE person_id =\n             (SELECT id FROM people WHERE name = 'Helena Bonham Carter'));", check=True)
add(id="S-45", case="movies", topic="Subqueries", level=3,
    prompt="How many different people starred in a movie together with Kevin Bacon (the one born in 1958)? Do not count Kevin Bacon himself.",
    answer=num(176),
    sql="SELECT COUNT(DISTINCT person_id)\nFROM stars\nWHERE movie_id IN (\n    SELECT movie_id FROM stars\n    WHERE person_id = (SELECT id FROM people WHERE name = 'Kevin Bacon' AND birth = 1958))\n  AND person_id <> (SELECT id FROM people WHERE name = 'Kevin Bacon' AND birth = 1958);", check=True)

# ===== Fiftyville
fv_setup = "Start with crime_scene_reports for 28 July 2020 on Chamberlin Street, then read the interviews from that day."
add(id="S-46", case="fiftyville", topic="Investigation", level=3, setup=fv_setup,
    prompt="Who is the thief?",
    answer=txt("Ernest"),
    sql="""SELECT p.name
FROM people p
WHERE p.license_plate IN (       -- left the courthouse lot 10:15 to 10:25
      SELECT license_plate FROM courthouse_security_logs
      WHERE year = 2020 AND month = 7 AND day = 28
        AND hour = 10 AND minute BETWEEN 15 AND 25 AND activity = 'exit')
  AND p.id IN (                  -- withdrew money on Fifer Street that morning
      SELECT ba.person_id FROM bank_accounts ba
      JOIN atm_transactions a ON a.account_number = ba.account_number
      WHERE a.year = 2020 AND a.month = 7 AND a.day = 28
        AND a.atm_location = 'Fifer Street' AND a.transaction_type = 'withdraw')
  AND p.phone_number IN (        -- made a call shorter than a minute
      SELECT caller FROM phone_calls
      WHERE year = 2020 AND month = 7 AND day = 28 AND duration < 60)
  AND p.passport_number IN (     -- on the earliest flight out the next day
      SELECT passport_number FROM passengers WHERE flight_id = (
        SELECT f.id FROM flights f
        JOIN airports a ON a.id = f.origin_airport_id
        WHERE a.city = 'Fiftyville' AND f.year = 2020 AND f.month = 7 AND f.day = 29
        ORDER BY f.hour, f.minute LIMIT 1));""", check=True)
add(id="S-47", case="fiftyville", topic="Investigation", level=2, setup=fv_setup,
    prompt="To which city did the thief escape?",
    answer=txt("London"),
    sql="SELECT d.city\nFROM flights f\nJOIN airports o ON o.id = f.origin_airport_id\nJOIN airports d ON d.id = f.destination_airport_id\nWHERE o.city = 'Fiftyville' AND f.year = 2020 AND f.month = 7 AND f.day = 29\nORDER BY f.hour, f.minute\nLIMIT 1;", check=True)
add(id="S-48", case="fiftyville", topic="Investigation", level=3, setup=fv_setup,
    prompt="Who is the thief's accomplice?",
    answer=txt("Berthold"),
    sql="SELECT r.name\nFROM phone_calls pc\nJOIN people t ON t.phone_number = pc.caller\nJOIN people r ON r.phone_number = pc.receiver\nWHERE t.name = 'Ernest'\n  AND pc.year = 2020 AND pc.month = 7 AND pc.day = 28 AND pc.duration < 60;", check=True)

# ===== P-card
pc_setup = "The pcards table holds only OSU transactions. Use Year and Month (taken from TransactionDate). Use FullName as stored unless the question says otherwise."
add(id="S-49", case="pcards", topic="COUNT", level=1, setup=pc_setup,
    prompt="What is the total number of P-card transactions in the database? (Label the column TotalTrans.)",
    answer=num(489178), sql="SELECT COUNT(*) AS TotalTrans\nFROM pcards;", check=True)
add(id="S-50", case="pcards", topic="WHERE", level=1, setup=pc_setup,
    prompt="How many transactions have an amount of $5,000 or more?",
    answer=num(1187), sql="SELECT COUNT(*) AS TotalTransGT5k\nFROM pcards\nWHERE Amount >= 5000;", check=True)
add(id="S-51", case="pcards", topic="WHERE", level=2, setup=pc_setup,
    prompt="What is the total dollar amount of returns (negative amounts) from January to March 2014, inclusive? Keep the sign.",
    answer=num(-157882.08, 0.01, "USD"),
    sql="SELECT ROUND(SUM(Amount), 2) AS TotalReturns2014Q1\nFROM pcards\nWHERE Year = 2014 AND Month BETWEEN 1 AND 3 AND Amount < 0;", check=True)
add(id="S-52", case="pcards", topic="GROUP BY", level=1, setup=pc_setup,
    prompt="Which cardholder had the most transactions in calendar year 2014?",
    answer=txt("G Hines"),
    sql="SELECT FullName, COUNT(*) AS NumTrans\nFROM pcards\nWHERE Year = 2014\nGROUP BY FullName\nORDER BY NumTrans DESC;", check=True)
add(id="S-53", case="pcards", topic="HAVING", level=2, setup=pc_setup,
    prompt="How many cardholders had more than 10 transactions in 2014?",
    answer=num(1515),
    sql="SELECT COUNT(*)\nFROM (\n  SELECT FullName\n  FROM pcards\n  WHERE Year = 2014\n  GROUP BY FullName\n  HAVING COUNT(*) > 10\n);", check=True)
add(id="S-54", case="pcards", topic="HAVING", level=2, setup=pc_setup,
    prompt="How many cardholders returned more than $1,000 worth of goods in 2014?",
    answer=num(149),
    sql="SELECT COUNT(*)\nFROM (\n  SELECT FullName, SUM(Amount) AS ReturnedGoodsValue\n  FROM pcards\n  WHERE Year = 2014 AND Amount < 0\n  GROUP BY FullName\n  HAVING SUM(Amount) < -1000   -- returns are negative\n);", check=True)
add(id="S-55", case="pcards", topic="LIKE", level=1, setup=pc_setup,
    prompt="How many 2014 transactions over $3,000 came from a vendor with Amazon anywhere in the name?",
    answer=num(7),
    sql="SELECT COUNT(*)\nFROM pcards\nWHERE Year = 2014 AND Amount > 3000 AND Vendor LIKE '%amazon%';", check=True)
add(id="S-56", case="pcards", topic="Calculated fields", level=2, setup=pc_setup,
    prompt="The state sales tax rate is 4.5%. Assuming all purchases were made net of sales tax, how much sales tax did OSU avoid paying on 2014 transactions? Round to the cent.",
    answer=num(1507686.68, 0.01, "USD"),
    sql="SELECT ROUND(SUM(Amount) * 0.045, 2) AS SalesTaxSaved\nFROM pcards\nWHERE Year = 2014;", check=True)
add(id="S-57", case="pcards", topic="CASE", level=2, setup=pc_setup,
    prompt="Rank 2014 returns by risk: $1,000 or more is High, $500 to under $1,000 is Medium, under $500 is Low. How many returns are High risk?",
    answer=num(114),
    sql="SELECT RiskRanking, COUNT(*)\nFROM (\n  SELECT CASE WHEN Amount <= -1000 THEN 'High'\n              WHEN Amount <= -500  THEN 'Medium'\n              ELSE 'Low' END AS RiskRanking\n  FROM pcards\n  WHERE Year = 2014 AND Amount < 0\n)\nGROUP BY RiskRanking\nORDER BY RiskRanking;   -- High comes first", check="col2")
add(id="S-58", case="pcards", topic="Subqueries", level=2, setup=pc_setup,
    prompt="How many 2014 transactions are greater than the average 2014 transaction amount?",
    answer=num(29640),
    sql="SELECT COUNT(*)\nFROM pcards\nWHERE Year = 2014\n  AND Amount > (SELECT AVG(Amount) FROM pcards WHERE Year = 2014);", check=True)
add(id="S-59", case="pcards", topic="Subqueries", level=3, setup=pc_setup,
    prompt="Consider vendors with purchases in both 2013 and 2014. Which vendor had the largest increase in spending from 2013 to 2014?",
    answer=txt("TFS FISHERSCI ECOM HUS"),
    sql="WITH s13 AS (SELECT Vendor, SUM(Amount) AS s FROM pcards WHERE Year = 2013 GROUP BY Vendor),\n     s14 AS (SELECT Vendor, SUM(Amount) AS s FROM pcards WHERE Year = 2014 GROUP BY Vendor)\nSELECT s14.Vendor, ROUND(s14.s - s13.s, 2) AS DiffSpending\nFROM s14 JOIN s13 ON s13.Vendor = s14.Vendor\nORDER BY DiffSpending DESC;", check=True)
add(id="S-60", case="pcards", topic="Subqueries", level=3, setup=pc_setup,
    prompt="By what percentage did the number of transactions change from 2011 to 2014? Use (n2014 - n2011) / n2011 × 100 and round to two decimals.",
    answer=num(-0.14, 0.005, "%"),
    sql="SELECT Year,\n       ROUND((COUNT(*) - (SELECT COUNT(*) FROM pcards WHERE Year = 2011)) * 100.0\n             / (SELECT COUNT(*) FROM pcards WHERE Year = 2011), 2) AS PercDiffFrom2011\nFROM pcards\nWHERE Year = 2014\nGROUP BY Year;", check="col2")
add(id="S-61", case="pcards", topic="Controls testing", level=2, setup=pc_setup,
    prompt="Control: a user shall not spend more than $50,000 per year. How many cardholders spent more than $50,000 in 2014?",
    answer=num(127),
    sql="SELECT COUNT(*)\nFROM (\n  SELECT FullName, SUM(Amount) AS TotalSpent\n  FROM pcards\n  WHERE Year = 2014\n  GROUP BY FullName\n  HAVING SUM(Amount) > 50000\n);", check=True)
add(id="S-62", case="pcards", topic="Controls testing", level=2, setup=pc_setup,
    prompt="Control: a user shall not spend more than $10,000 per month without approval. How many cardholder-month combinations in 2014 exceed $10,000?",
    answer=num(457),
    sql="SELECT COUNT(*)\nFROM (\n  SELECT FullName, Month, SUM(Amount) AS MonthTotal\n  FROM pcards\n  WHERE Year = 2014\n  GROUP BY FullName, Month\n  HAVING SUM(Amount) > 10000\n);", check=True)
add(id="S-63", case="pcards", topic="Controls testing", level=1, setup=pc_setup,
    prompt="Control: no single transaction may exceed $5,000. How many 2014 transactions exceed $5,000?",
    answer=num(33), sql="SELECT COUNT(*)\nFROM pcards\nWHERE Year = 2014 AND Amount > 5000;", check=True)
add(id="S-64", case="pcards", topic="Controls testing", level=3, setup=pc_setup,
    prompt="Split purchases, same card: find groups in 2014 where the same cardholder bought from the same vendor on the same TransactionDate, with more than one transaction and a combined total above $5,000. How many transaction lines are in these groups?",
    answer=num(254),
    sql="SELECT COUNT(*)\nFROM pcards\nWHERE Year = 2014\n  AND (FullName, Vendor, TransactionDate) IN (\n      SELECT FullName, Vendor, TransactionDate\n      FROM pcards\n      WHERE Year = 2014\n      GROUP BY FullName, Vendor, TransactionDate\n      HAVING COUNT(*) > 1 AND SUM(Amount) > 5000);", check=True)
add(id="S-65", case="pcards", topic="Controls testing", level=3, setup=pc_setup,
    prompt="Split purchases between cardholders: find vendor and TransactionDate combinations in 2014 where exactly two different cardholders bought from the vendor that day and the combined total exceeds $5,000. How many transaction lines are in these groups?",
    answer=num(150),
    sql="SELECT COUNT(*)\nFROM pcards\nWHERE Year = 2014\n  AND (Vendor, TransactionDate) IN (\n      SELECT Vendor, TransactionDate\n      FROM pcards\n      WHERE Year = 2014\n      GROUP BY Vendor, TransactionDate\n      HAVING COUNT(DISTINCT FullName) = 2 AND SUM(Amount) > 5000);", check=True)
add(id="S-66", case="pcards", topic="Controls testing", level=3, setup=pc_setup,
    prompt="Split purchases between vendors: find cardholder and TransactionDate combinations in 2014 with purchases at exactly two different vendors and a combined total above $5,000. How many transaction lines are in these groups?",
    answer=num(160),
    sql="SELECT COUNT(*)\nFROM pcards\nWHERE Year = 2014\n  AND (FullName, TransactionDate) IN (\n      SELECT FullName, TransactionDate\n      FROM pcards\n      WHERE Year = 2014\n      GROUP BY FullName, TransactionDate\n      HAVING COUNT(DISTINCT Vendor) = 2 AND SUM(Amount) > 5000);", check=True)
add(id="S-67", case="pcards", topic="Controls testing", level=3, setup=pc_setup,
    prompt="Food while travelling is prohibited. On days when a cardholder has a 2014 transaction whose MCC contains hotel, motel, resort or inn, how many of that cardholder's transactions on the same day have an MCC containing food or restaurant?",
    answer=num(99),
    sql="SELECT COUNT(*)\nFROM pcards\nWHERE Year = 2014\n  AND (MCC LIKE '%food%' OR MCC LIKE '%restaurant%')\n  AND (FullName, TransactionDate) IN (\n      SELECT FullName, TransactionDate\n      FROM pcards\n      WHERE Year = 2014\n        AND (MCC LIKE '%hotel%' OR MCC LIKE '%motel%'\n             OR MCC LIKE '%resort%' OR MCC LIKE '%inn%'));", check=True)
add(id="S-68", case="pcards", topic="Forensic tests", level=3, setup=pc_setup,
    prompt="Benford's law: for 2014 transactions of $1.00 or more, what percentage start with the digit 1? Round to three decimals.",
    answer=num(29.528, 0.001, "%"),
    sql="SELECT SUBSTR(CAST(Amount AS TEXT), 1, 1) AS FirstDigit,\n       ROUND(COUNT(*) * 100.0 /\n             (SELECT COUNT(*) FROM pcards WHERE Year = 2014 AND Amount >= 1), 3) AS Pct\nFROM pcards\nWHERE Year = 2014 AND Amount >= 1\nGROUP BY FirstDigit\nORDER BY FirstDigit;   -- Benford expects 30.1% for digit 1", check="col2")
add(id="S-69", case="pcards", topic="Forensic tests", level=3, setup=pc_setup,
    prompt="Possible duplicate payments: 2014 purchases (exclude returns) with the same cardholder, vendor, TransactionDate and amount, appearing more than once. How many transaction lines are possible duplicates?",
    answer=num(4924),
    sql="SELECT COUNT(*)\nFROM pcards\nWHERE Year = 2014 AND Amount > 0\n  AND (FullName, Vendor, TransactionDate, Amount) IN (\n      SELECT FullName, Vendor, TransactionDate, Amount\n      FROM pcards\n      WHERE Year = 2014 AND Amount > 0\n      GROUP BY FullName, Vendor, TransactionDate, Amount\n      HAVING COUNT(*) > 1);", check=True)
add(id="S-70", case="pcards", topic="Forensic tests", level=3, setup=pc_setup,
    prompt="Using the same duplicate definition, which cardholder has the most possible duplicate groups (not lines)?",
    answer=txt("J Bailey"),
    sql="SELECT FullName, COUNT(*) AS DuplicateGroups\nFROM (\n  SELECT FullName, Vendor, TransactionDate, Amount\n  FROM pcards\n  WHERE Year = 2014 AND Amount > 0\n  GROUP BY FullName, Vendor, TransactionDate, Amount\n  HAVING COUNT(*) > 1\n)\nGROUP BY FullName\nORDER BY DuplicateGroups DESC;", check=True)
add(id="S-71", case="pcards", topic="Forensic tests", level=2, setup=pc_setup,
    prompt="Round numbers may indicate fraud. How many 2014 transactions are whole-dollar, four-digit amounts ending in 000 (1000, 2000, ..., 9000)?",
    answer=num(149),
    sql="SELECT COUNT(*)\nFROM pcards\nWHERE Year = 2014\n  AND Amount BETWEEN 1000 AND 9999\n  AND Amount = CAST(Amount AS INTEGER)\n  AND CAST(Amount AS INTEGER) % 1000 = 0;", check=True)
add(id="S-72", case="pcards", topic="Data quality", level=2, setup=pc_setup,
    prompt="Some names are stored in different capitalisation (e.g. C STOVER and C Stover). How many distinct cardholder names are there if you ignore capitalisation?",
    answer=num(3120),
    sql="SELECT COUNT(DISTINCT UPPER(FullName)) AS IgnoringCase,\n       COUNT(DISTINCT FullName)        AS AsStored   -- 4,789\nFROM pcards;", check=True)

# ---------------------------------------------------------------- exams
# Each data manipulation exam: two Excel questions from different cases and
# two SQL questions from different databases.
EXAMS = [
    ["E-03", "E-28", "S-07", "S-52"],
    ["E-12", "E-39", "S-20", "S-30"],
    ["E-22", "E-46", "S-14", "S-63"],
    ["E-16", "E-33", "S-36", "S-62"],
    ["E-29", "E-50", "S-12", "S-32"],
    ["E-23", "E-40", "S-47", "S-55"],
    ["E-13", "E-58", "S-22", "S-61"],
    ["E-37", "E-61", "S-28", "S-57"],
    ["E-19", "E-48", "S-40", "S-64"],
    ["E-35", "E-53", "S-24", "S-69"],
    ["E-11", "E-62", "S-38", "S-54"],
    ["E-25", "E-44", "S-18", "S-67"],
]

# ---------------------------------------------------------------- validation
def open_db(case):
    files = DATASETS[case]["files"]
    path = os.path.join(ROOT, "data", files[0])
    if path.endswith(".zip"):
        tmp = os.path.join(tempfile.gettempdir(), "bank_" + case)
        os.makedirs(tmp, exist_ok=True)
        with zipfile.ZipFile(path) as z:
            name = z.namelist()[0]
            if not os.path.exists(os.path.join(tmp, name)):
                z.extract(name, tmp)
        path = os.path.join(tmp, name)
    return sqlite3.connect(path)

def matches(spec, got):
    if spec["type"] in ("number", "percent"):
        try: return abs(float(got) - spec["value"]) <= spec["tol"] + 1e-9
        except (TypeError, ValueError): return False
    if spec["type"] == "text":
        return str(got).strip().lower() in [a.lower() for a in spec["accept"]]
    return True

def validate():
    ids = [q["id"] for q in Q]
    assert len(ids) == len(set(ids)), "duplicate question IDs"
    for q in Q:
        assert q["case"] in DATASETS, q["id"] + ": unknown dataset"
        assert ("sql" in q) != ("steps" in q), q["id"] + ": needs either sql or steps"
        for f in DATASETS[q["case"]]["files"]:
            assert os.path.exists(os.path.join(ROOT, "data", f)), f + " missing"
    for e in EXAMS:
        for i in e: assert i in ids, "exam refers to unknown question " + i
    conns, failures = {}, []
    for q in Q:
        if "sql" not in q or q.get("check") is False: continue
        c = conns.setdefault(q["case"], open_db(q["case"]))
        row = c.execute(q["sql"]).fetchone()
        got = row[1] if q.get("check") == "col2" else row[0]
        ok = matches(q["answer"], got)
        print(("ok  " if ok else "FAIL"), q["id"], got)
        if not ok: failures.append(q["id"])
    if failures:
        sys.exit("Answers that no longer match their SQL: " + ", ".join(failures))

def export():
    for d in DATASETS.values():
        d["sizes"] = [os.path.getsize(os.path.join(ROOT, "data", f)) for f in d["files"]]
    questions = []
    for q in Q:
        out = {k: v for k, v in q.items() if k != "check"}
        out["tool"] = DATASETS[q["case"]]["tool"]
        questions.append(out)
    exams = [{"id": "M%02d" % (i + 1), "questions": e} for i, e in enumerate(EXAMS)]
    payload = {"datasets": DATASETS, "questions": questions, "exams": exams}
    with open(os.path.join(ROOT, "js", "bank.js"), "w", encoding="utf-8") as f:
        f.write("// Generated by tools/build_bank.py. Edit the questions there, not here.\n")
        f.write("window.BANK = " + json.dumps(payload, ensure_ascii=False, indent=1) + ";\n")
    print(f"Wrote {len(questions)} questions and {len(exams)} exams to js/bank.js")

if __name__ == "__main__":
    validate()
    export()
