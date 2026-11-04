"""
Task 2 improvement: feedback that teaches.

MISTAKES  - for each question, typical wrong methods. The wrong value is NOT
            typed in by hand: it is produced by running the wrong method
            (a wrong SQL query, or a wrong Excel step reproduced in pandas)
            on the real course data when tools/build_bank.py runs.
FOLLOWUPS - for each question, the "why" question an oral examiner would ask
            once the number is right, with a model answer.
"""
import os
from functools import lru_cache
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
D = lambda *p: os.path.join(ROOT, "data", *p)


def m(how, hint, tol=None):
    """how: SQL string (run on the question's database) or a Python function.
    tol: how close a typed answer must be to count as this mistake
    (defaults to the question's own tolerance)."""
    return {"how": how, "hint": hint, "tol": tol}


# ------------------------------------------------------------- data loaders
@lru_cache(None)
def nyc():
    d = pd.read_csv(D("excel", "NYC_Film_Permits.csv"), dtype={"ZipCode": str})
    for c in ["StartDateTime", "EndDateTime", "EnteredOn"]:
        d[c] = pd.to_datetime(d[c], format="%m/%d/%Y %H:%M")
    return d

def shoots(): d = nyc(); return d[d.EventType == "Shooting Permit"]

@lru_cache(None)
def etl2():
    d = pd.read_excel(D("excel", "ETL_Case2.xlsx"), sheet_name="Case 2")
    p = d.EmployeeCode.str.extract(r"^([A-Z]{3})(\d{4})-(\d+)([WM])$"); p.columns = ["Loc", "Emp", "Plant", "Pay"]
    d = d.join(p); d["LP"] = d.Loc + "-" + d.Plant
    return d

@lru_cache(None)
def etl3():
    d = pd.read_excel(D("excel", "ETL_Case3.xlsx"), sheet_name="Case 3 data")
    p = d.EmployeeCode.str.extract(r"^([A-Za-z]+)(\d+)-(\d+)([A-Za-z]+)$"); p.columns = ["Loc", "Emp", "Plant", "Pay"]
    d = d.join(p); d["LP"] = d.Loc + "-" + d.Plant
    return d

@lru_cache(None)
def etl4():
    x = pd.read_excel(D("excel", "ETL_Case4.xlsx"), sheet_name=None)
    je = x["JELineItems"].copy()
    for c in ["Debit", "Credit"]: je[c] = pd.to_numeric(je[c], errors="coerce")
    return je, x["BusinessUnits"], x["ChartOfAccounts"].iloc[:, :4], x["PreparerInfo"], x["Source"]

@lru_cache(None)
def ic():
    a = pd.read_csv(D("excel", "IntegrateCo_2015payroll.csv"), sep="|", dtype={"Job": str})
    b = pd.read_csv(D("excel", "IntegrateCo_2016payroll.csv"), sep="|", dtype={"Project": str})
    jc = lambda s: s.str.extract(r"^\d{2}[A-Z]?(\d{3})")[0]
    a["JC"] = jc(a.Job); b["JC"] = jc(b.Project)
    a["Gross"] = a.Reg_Pay + a.OT_Pay; a["Name"] = a.First_Name + " " + a.Last_Name
    return a, b

@lru_cache(None)
def rest():
    x = pd.read_excel(D("excel", "Restaurant_data.xlsm"), sheet_name=None)
    s, w, g = x["salesData"], x["weatherData"], x["gameData"]
    d = s.groupby("date")[["netTotal", "netTotal_7", "netTotal_364"]].sum().reset_index()
    d = d.merge(w, on="date", how="left").merge(g[["date", "gameDay"]], on="date", how="left")
    d["gameDay"] = d.gameDay.fillna(0)
    item = s.merge(w, on="date", how="left").merge(g[["date", "gameDay"]], on="date", how="left")
    item["gameDay"] = item.gameDay.fillna(0)
    return s, d, item

def ols(y, X):
    import statsmodels.api as sm
    return sm.OLS(y, sm.add_constant(X)).fit()


# ------------------------------------------------------------- mistakes
MISTAKES = {
    # NYC film permits
    "E-01": [m(lambda: len(nyc()) + 1, "That count includes the header row. Count data rows only.")],
    "E-03": [m(lambda: int(nyc().ZipCode.isna().sum() + (~nyc().ZipCode.dropna().str.fullmatch(r"\d{5}")).sum()),
               "You also counted the zip codes that are filled in but invalid (83). Missing means blank.")],
    "E-04": [m(lambda: int(nyc().ZipCode.isna().sum() + (~nyc().ZipCode.dropna().str.fullmatch(r"\d{5}")).sum()),
               "You included the blank zip codes. The question asks for values that are filled in but not five digits.")],
    "E-11": [m(lambda: int((nyc().Category == "Student").sum()),
               "You counted student permits of every event type. Filter on EventType = Shooting Permit first.")],
    "E-12": [m(lambda: round(nyc()["CommunityBoard(s)"].astype(str).str.contains(",").mean(), 4),
               "That is the share across all event types. The question only covers shooting permits.")],
    "E-13": [m(lambda: int(next(y for y, r in shoots().assign(y=shoots().EnteredOn.dt.year).groupby(["y", "Borough"]).size().unstack().iterrows()
                                if r["Brooklyn"] > r["Manhattan"])),
               "You used the year of EnteredOn. The question asks for the year the shoot starts (StartDateTime).")],
    "E-14": [m(lambda: round(shoots().ParkingHeld.str.contains("BROADWAY", case=False).mean(), 2),
               "You divided by all shooting permits. The question asks for the share of Manhattan shoots only.")],
    "E-16": [m(lambda: round(((shoots().EndDateTime - shoots().StartDateTime).dt.total_seconds() / 86400).mean(), 2),
               "That is the average in days. Excel stores date-times as days, so multiply the difference by 24.", 0.01)],
    "E-17": [m(lambda: round(((shoots().EndDateTime - shoots().StartDateTime).dt.total_seconds() / 3600).min(), 4),
               "That is the shortest shoot in hours. Multiply by 60 to get minutes.", 0.001)],
    "E-18": [m(lambda: round(((shoots().StartDateTime - shoots().EnteredOn).dt.total_seconds() / 86400).mean(), 2),
               "Right calculation, but round to the nearest whole day.", 0.05)],
    "E-20": [m(lambda: round((shoots().StartDateTime.dt.dayofweek == 4).mean(), 4),
               "You only checked whether the shoot starts on a Friday. Shoots that start Thursday and run past midnight also include a Friday.")],

    # ETL case 1
    "E-21": [m(lambda: 22, "Nothing was removed. The Aptevo 2018 row appears twice; use Data > Remove Duplicates on all columns.")],
    "E-23": [m(lambda: 25900, "That is still in millions. 25900 M means 25,900 × 1,000,000.")],
    "E-25": [m(lambda: 9700000 + 7100000 + 30600000 + 30600000, "The duplicate Aptevo 2018 row is still in your data, so 2018 is counted twice."),
             m(lambda: 9700 + 7100 + 30600, "Those are still thousands (K). Multiply by 1,000.")],

    # ETL case 2
    "E-27": [m(lambda: int(etl2().Plant.nunique()),
               "You counted distinct PlantIDs. Plant numbers repeat across countries, so the identifier must combine Location and PlantID.")],
    "E-28": [m(lambda: int((etl2().Plant == "12").sum()),
               "You counted plant 12 in every country. USA-12 means plant 12 in the USA only.")],
    "E-29": [m(lambda: int((etl2().Loc == "GER").sum()), "That is all German employees. Add the condition PayPeriod = W.")],
    "E-31": [m(lambda: int((etl2().Pay == "W").sum()), "That is the number of weekly-paid employees. Monthly is M.")],

    # ETL case 3
    "E-33": [m(lambda: int(((etl3().Loc == "Japan") & (etl3().Pay == "M")).sum()),
               "You only counted M. Monthly pay is written as both M and Mo; standardise with LEFT(pay,1).")],
    "E-34": [m(lambda: int((etl3().Pay == "M").sum()), "That counts the codes ending in plain M. The question asks for Mo.")],
    "E-35": [m(lambda: int(etl3().LP.str.startswith("US-1").sum()),
               "Your match also counts US-10, US-11 and so on. Compare the whole LocationPlantID, not just its beginning.")],

    # ETL case 4
    "E-37": [m(lambda: int((~etl4()[0].PreparerID.isin(etl4()[3].PreparerID)).sum()),
               "You matched on PreparerID alone. PreparerID restarts in every business unit, so only PreparerID and BusinessUnitID together identify a preparer.")],
    "E-41": [m(lambda: 398321.61, "Right size, wrong sign. Revenue lines are credits, so their Amount is negative.")],
    "E-43": [m(lambda: 0, "That is the sum of Amount (debits and credits cancel out). The question asks for the Debit column.")],

    # IntegrateCo
    "E-44": [m(lambda: round(ic()[0].Reg_Pay.sum(), 2), "That is regular pay only. Gross pay is Reg_Pay + OT_Pay.")],
    "E-46": [m(lambda: round(ic()[0].Gross.sum() - ic()[1].Gross_Wages.sum(), 2), "Right size, wrong direction. Take 2016 minus 2015, so an increase is positive.")],
    "E-48": [m(lambda: "009", "009 only has wages in 2016. The question asks for job codes with wages in both years.")],
    "E-51": [m(lambda: float(ic()[0].groupby("Emp_No").OT_Hrs.sum().max()), "That is the number of overtime hours. The question asks for the overtime pay.")],
    "E-53": [m(lambda: round(ic()[1].Gross_Wages.sum(), 2), "That is gross wages only. Add SocSec_Medicare, FUTA, SUTA and Work_Comp.")],
    "E-54": [m(lambda: int(((ic()[0].Reg_Hrs < 40) & (ic()[0].OT_Hrs > 0)).sum()),
               "You checked single rows. Each row is one job code, so first add up an employee's hours per pay date, then test the totals.")],
    "E-55": [m(lambda: round(ic()[0].assign(M=pd.to_datetime(ic()[0].Pay_Date).dt.month).groupby("M").Gross.sum().max(), 2),
               "That is May's total. The question asks how much May exceeds the six-month average.")],

    # Restaurant
    "E-58": [m(lambda: len(rest()[0]), "That is the number of rows in salesData. Each row is one menu item on one date; aggregate to dates first.")],
    "E-60": [m(lambda: round(1359.1615 + 0.5858 * float(rest()[1].iloc[-1].netTotal_7), 2),
               "You used the last date's netTotal_7 as input. Seven days after the last date, the 7-day lag is the last date's own sales.")],
    "E-61": [m(lambda: round(float(ols(rest()[2].netTotal, rest()[2][["tmax"]]).params["tmax"]), 2),
               "You ran the regression on item-level rows. Aggregate salesData to daily totals before merging the weather.", 0.01)],
    "E-62": [m(lambda: round(float(ols(rest()[2].netTotal, rest()[2][["gameDay"]]).params["gameDay"]), 2),
               "You ran the regression on item-level rows. The question is about total daily sales, so aggregate to one row per date first.", 0.05)],
    "E-63": [m(lambda: round(float(ols(rest()[1].netTotal, rest()[1].assign(gx=rest()[1].gameDay * rest()[1].netTotal_364)[["netTotal_364", "gameDay", "gx"]]).rsquared_adj), 3),
               "That is the Adjusted R Square. The question asks for R Square, the row above it.", 0.001)],

    # Chinook
    "S-03": [m("SELECT LastName FROM Customer ORDER BY LastName LIMIT 1 OFFSET 3;", "OFFSET counts rows to skip. The third row needs OFFSET 2.")],
    "S-08": [m("SELECT COUNT(*) FROM Invoice WHERE BillingCountry LIKE '%C%';", "'%C%' finds a C anywhere in the name. Starts with C is 'C%'.")],
    "S-09": [m("SELECT COUNT(*) FROM Customer;", "That counts every customer. Customers without a company have NULL in Company; filter with IS NOT NULL.")],
    "S-12": [m("SELECT COUNT(*) FROM Employee WHERE strftime('%w', BirthDate) = '1';", "In SQLite strftime('%w') returns 0 for Sunday, not 1 (1 is Monday).")],
    "S-14": [m("SELECT MAX(n) FROM (SELECT COUNT(*) AS n FROM Invoice GROUP BY BillingCountry);",
               "That is the number of invoices. The question asks for their total value: SUM(Total), not COUNT(*).")],
    "S-18": [m("SELECT COUNT(*) FROM (SELECT TrackId FROM InvoiceLine GROUP BY TrackId);", "That counts every track downloaded at least once. Keep only tracks whose total downloads equal 2 (HAVING).")],
    "S-21": [m("SELECT COUNT(DISTINCT TrackId) FROM InvoiceLine;", "That counts distinct tracks. Join to Track and count distinct AlbumId.")],
    "S-28": [m("SELECT COUNT(*) FROM songs WHERE danceability > 0.6 OR energy > 0.6 OR valence > 0.6;", "With OR a song needs only one of the three. All three means AND.")],
    "S-35": [m("SELECT COUNT(*) FROM movies WHERE year > 2017;", "> 2017 leaves out 2017 itself. Use >= 2017.")],
    "S-36": [m("SELECT COUNT(*) FROM ratings WHERE rating >= 9.0;", ">= also counts movies rated exactly 9.0. The question says greater than 9.0.")],
    "S-39": [m("SELECT COUNT(*) FROM movies WHERE year = 2011;", "That counts all 2011 movies. Join to ratings so only movies with a rating remain.")],
    "S-41": [m("SELECT COUNT(st.person_id) FROM stars st JOIN movies m ON m.id = st.movie_id WHERE m.year = 2003;", "People who starred in several 2003 movies are counted more than once. Use COUNT(DISTINCT ...).")],
    "S-42": [m("SELECT COUNT(d.person_id) FROM directors d JOIN ratings r ON r.movie_id = d.movie_id WHERE r.rating >= 8.0;", "Directors with several highly rated movies are counted more than once. Use COUNT(DISTINCT ...).")],
    "S-45": [m("""SELECT COUNT(DISTINCT person_id) FROM stars WHERE movie_id IN (SELECT movie_id FROM stars WHERE person_id = (SELECT id FROM people WHERE name = 'Kevin Bacon' AND birth = 1958));""",
               "Kevin Bacon himself is still in your count. Exclude his id.")],

    # P-card
    "S-50": [m("SELECT COUNT(*) FROM pcards WHERE Amount > 5000;", "> 5000 leaves out transactions of exactly $5,000. The question says 5,000 or more.")],
    "S-51": [m("SELECT ROUND(-SUM(Amount),2) FROM pcards WHERE Year = 2014 AND Month BETWEEN 1 AND 3 AND Amount < 0;", "Right size, but returns are negative amounts. Keep the sign."),
             m("SELECT ROUND(SUM(Amount),2) FROM pcards WHERE Year = 2014 AND Amount < 0;", "That is the total for all of 2014. Limit to months 1 to 3.")],
    "S-53": [m("SELECT COUNT(*) FROM (SELECT FullName FROM pcards WHERE Year = 2014 GROUP BY FullName HAVING COUNT(*) >= 10);", ">= 10 includes cardholders with exactly 10. The question says more than 10.")],
    "S-54": [m("SELECT COUNT(*) FROM (SELECT FullName FROM pcards WHERE Year = 2014 AND Amount < 0 GROUP BY FullName HAVING SUM(Amount) > -1000);",
               "Returns are negative, so 'more than $1,000 returned' means SUM(Amount) < -1000. Your condition kept the small returners.")],
    "S-56": [m("SELECT ROUND(SUM(Amount) * 0.045, 2) FROM pcards;", "That is the tax saved over all years. Filter on Year = 2014.")],
    "S-57": [m("SELECT COUNT(*) FROM pcards WHERE Year = 2014 AND Amount < 0 AND Amount < -1000;", "Strictly less than -1000 leaves out returns of exactly $1,000. High risk is $1,000 or more: Amount <= -1000.")],
    "S-58": [m("SELECT COUNT(*) FROM pcards WHERE Year = 2014 AND Amount > (SELECT AVG(Amount) FROM pcards);", "Your average covers all years. The subquery also needs WHERE Year = 2014.")],
    "S-60": [m("""SELECT ROUND((COUNT(*) - (SELECT COUNT(*) FROM pcards WHERE Year = 2010)) * 100.0 / (SELECT COUNT(*) FROM pcards WHERE Year = 2010), 2) FROM pcards WHERE Year = 2014;""",
               "You compared with 2010, which only has a few months of data. The question uses 2011 as the base.")],
    "S-61": [m("SELECT COUNT(*) FROM (SELECT UPPER(FullName) FROM pcards WHERE Year = 2014 GROUP BY UPPER(FullName) HAVING SUM(Amount) > 50000);",
               "You merged names that differ only in capitalisation. That is defensible, but this question asks for FullName as stored.")],
    "S-62": [m("SELECT COUNT(*) FROM (SELECT Month FROM pcards WHERE Year = 2014 GROUP BY Month HAVING SUM(Amount) > 10000);", "You grouped by month only. The control is per cardholder per month: GROUP BY FullName, Month.")],
    "S-63": [m("SELECT COUNT(*) FROM pcards WHERE Year = 2014 AND Amount >= 5000;", ">= also counts transactions of exactly $5,000, which the control allows.")],
    "S-64": [m("SELECT COUNT(*) FROM (SELECT 1 FROM pcards WHERE Year = 2014 GROUP BY FullName, Vendor, TransactionDate HAVING COUNT(*) > 1 AND SUM(Amount) > 5000);",
               "That is the number of groups. The question asks for the transaction lines inside those groups."),
             m("SELECT COUNT(*) FROM pcards WHERE Year = 2014 AND (FullName, Vendor, TransactionDate) IN (SELECT FullName, Vendor, TransactionDate FROM pcards WHERE Year = 2014 GROUP BY FullName, Vendor, TransactionDate HAVING SUM(Amount) > 5000);",
               "Without COUNT(*) > 1 you also include single transactions over $5,000. A split needs at least two swipes.")],
    "S-65": [m("SELECT COUNT(*) FROM (SELECT 1 FROM pcards WHERE Year = 2014 GROUP BY Vendor, TransactionDate HAVING COUNT(DISTINCT FullName) = 2 AND SUM(Amount) > 5000);",
               "That is the number of vendor-day groups. Count the transaction lines inside them.")],
    "S-66": [m("SELECT COUNT(*) FROM (SELECT 1 FROM pcards WHERE Year = 2014 GROUP BY FullName, TransactionDate HAVING COUNT(DISTINCT Vendor) = 2 AND SUM(Amount) > 5000);",
               "That is the number of cardholder-day groups. Count the transaction lines inside them.")],
    "S-67": [m("SELECT COUNT(*) FROM pcards WHERE Year = 2014 AND (MCC LIKE '%food%' OR MCC LIKE '%restaurant%');",
               "That counts all food and restaurant purchases. Only those on the same day as a hotel purchase by the same cardholder are suspicious.")],
    "S-68": [m("SELECT ROUND(SUM(SUBSTR(CAST(Amount AS TEXT),1,1)='1') * 100.0 / COUNT(*), 3) FROM pcards WHERE Year = 2014;",
               "Your denominator includes returns and amounts under $1. Benford's analysis uses amounts of $1.00 or more only.")],
    "S-69": [m("SELECT COUNT(*) FROM (SELECT 1 FROM pcards WHERE Year = 2014 AND Amount > 0 GROUP BY FullName, Vendor, TransactionDate, Amount HAVING COUNT(*) > 1);",
               "That is the number of duplicate groups. Count every transaction line in them.")],
    "S-72": [m("SELECT COUNT(DISTINCT FullName) FROM pcards;", "That is the count as stored. Ignoring capitalisation means COUNT(DISTINCT UPPER(FullName)).")],
}


# ------------------------------------------------------------- examiner follow-ups
# (question the examiner asks once your number is right, model answer)
FOLLOWUPS = {
    "E-01": ("Why does the row number of the last record differ from the record count?",
             "Row 1 holds the headers, so the last row number is the record count plus one. Counting the rows of the table avoids that off-by-one error."),
    "E-02": ("Why check the number of columns right after importing a CSV?",
             "If a delimiter appears inside a field without a text qualifier, rows split into extra columns. A column count that differs from the number of headers signals an import problem."),
    "E-03": ("Why does it matter whether a value is missing or invalid?",
             "Missing values are visibly absent and can be excluded. Invalid values look like data and silently distort results, for example 83 counted as a zip code. They need different treatment and different follow-up with the data owner."),
    "E-04": ("Why is a zip code better stored as text than as a number?",
             "A zip code is an identifier, not a quantity. As a number, leading zeros disappear (07030 becomes 7030), and a five-digit check would then fail on valid codes."),
    "E-05": ("What would you do with a column that has the same value in every row?",
             "Drop it from the analysis, because it carries no information, and reducing volume is good ETL practice. Document its value so nothing is lost."),
    "E-06": ("How does Excel store this date and time, and why does that matter?",
             "As a serial number: days since 0 January 1900, with the time of day as a fraction. That is why MIN works on dates and why subtracting two dates gives days."),
    "E-07": ("What would it tell you if the newest EnteredOn were much older than expected?",
             "The extract might be incomplete for recent periods. Compare it with the extraction date before drawing conclusions about recent activity."),
    "E-08": ("Why use a PivotTable or UNIQUE rather than scrolling through the column?",
             "It is complete and repeatable: it catches rare values and spelling variants, and it can be refreshed when new data arrives."),
    "E-09": ("Why do the later questions restrict the analysis to this event type?",
             "Different event types are different activities. Mixing them would compare shoots with load-ins and rigging, so the population must match the question."),
    "E-10": ("Could the answer change if you had not filtered on shooting permits first?",
             "Yes. The filter defines the population; other event types have their own category mix. A conclusion is only valid for the population you analysed."),
    "E-11": ("Why COUNTIFS with two conditions rather than COUNTIF?",
             "Both conditions must hold: the permit is a shooting permit and the category is Student. COUNTIF on Category alone counts student permits of every event type (282)."),
    "E-12": ("Why does a comma in CommunityBoard(s) mean more than one board?",
             "Several values are stored in one cell, separated by commas, so a comma means at least two boards. It is the same multi-value-in-one-cell problem as in the ETL case."),
    "E-13": ("Why assign shoots to a year by StartDateTime rather than EnteredOn?",
             "The question is about when shoots take place. EnteredOn is the application date, which can fall in the previous year for shoots in early January."),
    "E-14": ("What is a weakness of searching ParkingHeld for the word BROADWAY?",
             "It can include false positives (a street such as Broadway Terrace) and miss misspellings. A text search is a filter that you should spot-check."),
    "E-15": ("Why is the date filter applied to EnteredOn here?",
             "The question is about applications submitted since 2013, and the application date is EnteredOn."),
    "E-16": ("Why do you multiply the difference by 24?",
             "Excel stores date-times as days, so End minus Start is in days. Multiplying by 24 converts days to hours."),
    "E-17": ("A one-minute shoot looks odd. What would you do with it?",
             "Treat it as a possible data-entry error: check whether it affects the results, report it and ask the data owner instead of silently deleting it."),
    "E-18": ("Could a lead time be negative, and what would that mean?",
             "Yes, if a permit was entered after the shoot started. That is either a late registration or a data error, and worth flagging as a control issue."),
    "E-19": ("Why use TEXT(date, \"dddd\") rather than WEEKDAY?",
             "TEXT returns the day name directly, which reads well in a PivotTable. WEEKDAY returns a number whose meaning depends on its second argument."),
    "E-20": ("Why is it not enough to check the day the shoot starts?",
             "Shoots can run past midnight or over several days. A Thursday-to-Friday shoot involves a Friday, so every calendar day from start to end has to be checked."),
    "E-21": ("How do you know the removed row was a duplicate and not a second legitimate record?",
             "Every field is identical, and a company has one balance sheet per year. Without a unique identifier it is still an assumption, so you document it."),
    "E-22": ("How would a text qualifier have prevented this problem?",
             "Double quotes around the name (\"Apple, Inc.\") tell the import that the comma is text. Alternatively use the pipe delimiter that the AICPA Audit Data Standards recommend."),
    "E-23": ("Why must all values be in the same unit before analysis?",
             "Otherwise sums and comparisons are meaningless: 25900 would look smaller than 3,220,000,000 although it is about eight times larger."),
    "E-24": ("Why is an inconsistent ticker a problem?",
             "The ticker is the identifier. Three spellings split Amazon into three companies in pivots and lookups, so per-company totals are wrong."),
    "E-25": ("Which two transformations did you need?",
             "Remove the duplicate 2018 row and convert the K values to dollars. Both must be done before summing; doing only one gives a wrong total."),
    "E-26": ("What would you do with rows without a ticker in a real engagement?",
             "Keep them, since the company name still identifies them. Fill in the ticker from a reliable source or ask the client, and document the change."),
    "E-27": ("Why is PlantID alone not a unique identifier?",
             "Every country numbers its plants from 10 upwards, so plant 12 exists in several countries. Only Location and PlantID together identify one plant."),
    "E-28": ("Why build a combined LocationPlantID instead of filtering two columns?",
             "For one count both work, but a single key can be used directly in COUNTIF, lookups and PivotTables, and it is what the manager asked for."),
    "E-29": ("Why extract PayPeriod into its own column instead of searching the code for W?",
             "A search for W could match other parts of a code. A separate field makes the filter exact and reusable."),
    "E-30": ("Why convert PlantID to a number before taking the maximum?",
             "Extracted with MID it is text. MAX ignores text, and text sorts character by character (\"9\" after \"26\"). VALUE makes the comparison numeric."),
    "E-31": ("Text to Columns or formulas: which is better for a repeatable process?",
             "Formulas, because they recalculate when new data is pasted in. Text to Columns has to be redone by hand every time."),
    "E-32": ("Why can you not use fixed positions as in Case 2?",
             "Location is 2 to 6 letters and EmpID 1 to 3 digits, so the parts start at different positions. You have to locate the first digit and the hyphen in each code."),
    "E-33": ("How did you treat M and Mo, and why is that allowed?",
             "The case states that both mean monthly, so standardising them to one value is a legitimate transformation, which you document."),
    "E-34": ("What does the mix of M and Mo tell you about the source system?",
             "The field is typed by hand without validation. Recommend a drop-down or validation rule so the data is clean at the source."),
    "E-35": ("Why can a wildcard search for US-1 give a wrong count?",
             "US-1* also matches US-10 to US-17. You have to compare the complete identifier."),
    "E-36": ("Why is a control total like the sum of EmpID useful?",
             "One wrongly extracted row changes the total, so you can confirm 597 extractions at once instead of inspecting every row."),
    "E-37": ("A VLOOKUP on PreparerID alone returns a name for every line. Why is that dangerous?",
             "It returns the first preparer with that ID, whatever the business unit. The result looks complete but attributes entries to the wrong person, which undermines segregation-of-duties testing."),
    "E-38": ("Why do systems such as GUESTSYS and POS appear as preparers, and why does it matter for audit?",
             "Entries recorded in a subsystem are posted automatically. Automated entries are tested through system controls, manual entries through individual testing, so you separate them."),
    "E-39": ("Why INDEX/MATCH or XLOOKUP instead of VLOOKUP?",
             "They do not depend on the lookup column being leftmost or on a column number, so the formula survives inserted columns and can match on several conditions."),
    "E-40": ("Why look up AccountClass instead of choosing GL account numbers by hand?",
             "The chart of accounts is the authoritative mapping. Hand-picked account numbers miss new accounts and make the process unrepeatable."),
    "E-41": ("Why is the revenue total negative?",
             "In this file credits are negative. Revenue normally carries a credit balance, so its amounts sum to a negative number."),
    "E-42": ("Which join type does your lookup correspond to, and why is it the right one?",
             "A left join: every journal line is kept and the business unit is added where it matches. An inner join could drop unmatched lines without anyone noticing."),
    "E-43": ("Why is \"total Amount equals zero\" a useful check?",
             "In double-entry bookkeeping debits equal credits. If the total is not zero after loading, lines were lost or duplicated in the extract."),
    "E-44": ("Why can you not compare 2015 Reg_Pay directly with 2016 Gross_Wages?",
             "The two systems define fields differently: Gross_Wages already includes overtime. You first build the same measure for 2015, Reg_Pay + OT_Pay."),
    "E-45": ("What would you check before trusting the 2016 total?",
             "Data quality in the new system: rows without employee numbers, invalid job codes and whether the file covers all six months."),
    "E-46": ("Before telling Noah why payroll rose, what could make this difference misleading?",
             "The system change: phantom entries, new job codes and a different level of aggregation. Part of the change may come from the data rather than the business."),
    "E-47": ("What would you do with rows that have an invalid job code?",
             "Keep them in the totals but flag them and ask the client what they are. Deleting them would change total payroll without an explanation."),
    "E-48": ("Why leave out job codes that only exist in 2016?",
             "A change needs a 2015 base. Codes such as 009 (the new foreign plant) are new activity and should be explained separately, not ranked as increases."),
    "E-49": ("Which control weakness do the phantom entries point to?",
             "The new system accepts payroll lines without a valid employee number, so payments cannot be traced to a person: a fraud and accuracy risk."),
    "E-50": ("Is 32,951 material? How would you decide?",
             "Compare it with what Noah asked about: it is about 12% of the 266,000 increase, so it matters for the explanation even though it is small relative to total payroll."),
    "E-51": ("Why aggregate by employee number rather than by name?",
             "Names are not unique and can be spelled differently. Emp_No is the stable identifier."),
    "E-52": ("Noah wants to move employees between job codes to cut overtime. What else would you examine?",
             "Whether the overtime is concentrated in a few people rather than in the job code, and whether workload or staffing explains it. Moving people does not remove the work."),
    "E-53": ("Should the phantom entries be part of total employee cost?",
             "Yes, they were paid, so they are a cost. Report them separately because they are unexplained."),
    "E-54": ("Why add up hours per employee and pay date before testing?",
             "Each row is one job code. The 40-hour rule applies to total hours in the period, so it can only be tested on the employee's total."),
    "E-55": ("Why might May be higher than the other months?",
             "May may contain more pay dates than other months, or there was extra activity. Check the number of pay runs per month before concluding that wages rose."),
    "E-56": ("Why include overtime hours in the denominator?",
             "Gross wages include overtime pay, so the hours must include overtime hours. Otherwise pay per hour is overstated."),
    "E-57": ("Is this total the same as revenue in the income statement?",
             "No. netTotal is before tax and covers only menu items recorded in the POS data; other revenue and adjustments are not included."),
    "E-58": ("Why aggregate before merging with the weather data?",
             "Weather has one row per date and sales one row per item per date. Merging first repeats the weather on every item row, so the analysis runs at the wrong level."),
    "E-59": ("What would you check before treating 27 April as a normal day?",
             "Whether something special happened: an event, a large catering order or a data error. Outliers have a strong influence on regressions."),
    "E-60": ("How confident should Bob be in this prediction?",
             "Not very: R² is 0.38, so most of the day-to-day variation is unexplained, and a single past day is a noisy predictor. Present a range, not one number."),
    "E-61": ("The coefficient is significant but R² is only 0.02. How do you explain that to Bob?",
             "Warmer days really do sell slightly more, but temperature explains only 2% of the variation, so on its own it is useless for planning."),
    "E-62": ("Does this prove that game days cause higher sales?",
             "Not on its own. Game days are autumn Saturdays, so the weekday or season may explain part of the difference. You would add those as control variables."),
    "E-63": ("The interaction is not significant. What do you tell Bob?",
             "There is no evidence that games boost sales more on days that were already busy. Last year's sales are the main predictor, and with only 13 game days the estimate is uncertain."),
    "S-01": ("Why look at a table's structure before writing queries?",
             "To know the column names, data types and keys, so you join and filter on the right fields."),
    "S-02": ("Why is \"the first 5 rows\" unreliable without ORDER BY?",
             "SQL tables have no guaranteed order. Without ORDER BY the database may return rows in a different order, so the result is not reproducible."),
    "S-03": ("Why OFFSET 2 for the third row?",
             "OFFSET is the number of rows to skip. Skipping two rows leaves the third one."),
    "S-04": ("Why is COUNT(*) a good first query on a new table?",
             "It shows the volume and gives a control total to reconcile with the source system."),
    "S-05": ("Why not >= 20?",
             "The question says greater than. Whether values exactly at the boundary are included must come from the wording."),
    "S-06": ("BETWEEN 10 AND 20 gives the same result here. Why is it still wrong?",
             "BETWEEN includes both ends. It matches only because no invoice is exactly 10 or 20; on other data it would give a wrong count."),
    "S-07": ("Why IN rather than three OR conditions?",
             "Same result, but IN is shorter and avoids errors when OR is combined with AND without brackets."),
    "S-08": ("What is the difference between 'C%' and '%C%'?",
             "'C%' means starts with C; '%C%' means contains a C anywhere."),
    "S-09": ("Why does Company = NULL not work?",
             "NULL means unknown, and any comparison with unknown is not true. You have to use IS NULL or IS NOT NULL."),
    "S-10": ("The table is tiny. Why still count with SQL?",
             "The query documents how you got the number and can be rerun when the table grows or a reviewer checks your work."),
    "S-11": ("How can LENGTH help with data quality?",
             "It reveals values that are truncated, too long or padded with spaces, for example identifiers that should all have the same length."),
    "S-12": ("How did you know which number SQLite uses for Sunday?",
             "From the documentation: strftime('%w') returns 0 for Sunday to 6 for Saturday. Systems differ (Excel's WEEKDAY uses 1 for Sunday by default), so you check."),
    "S-13": ("Why divide by 365.25?",
             "julianday gives a difference in days; 365.25 accounts for leap years when converting to years."),
    "S-14": ("Why group by BillingCountry rather than the customer's current country?",
             "The question is about invoices, and the invoice records where it was billed. A customer could have moved since."),
    "S-15": ("What is the relationship between Invoice and InvoiceLine?",
             "One-to-many: one invoice has many lines, and InvoiceLine.InvoiceId is the foreign key to Invoice."),
    "S-16": ("Why do COUNT and COUNT(DISTINCT) give different results here?",
             "COUNT counts rows; COUNT(DISTINCT) counts unique values, here the two price points."),
    "S-17": ("Why SUM(Quantity) rather than COUNT(*)?",
             "A line could have a quantity above 1. Here every quantity is 1, so both agree, but SUM is correct by definition."),
    "S-18": ("Why HAVING and not WHERE?",
             "WHERE filters rows before grouping. The number of downloads per track only exists after GROUP BY, so it is filtered with HAVING."),
    "S-19": ("Why does MAX work on InvoiceDate in SQLite?",
             "The dates are stored as ISO text (YYYY-MM-DD), which sorts in date order. Dates stored as M/D/YYYY text would not."),
    "S-20": ("Why do you need two joins?",
             "InvoiceLine only has TrackId. The genre name is in Genre, which you reach through Track.GenreId."),
    "S-21": ("Why COUNT(DISTINCT AlbumId)?",
             "An album appears once for every track sold from it. DISTINCT counts each album once."),
    "S-22": ("Which keys connect an invoice to an employee?",
             "Invoice.CustomerId to Customer, then Customer.SupportRepId to Employee.EmployeeId."),
    "S-23": ("Why join through Album to reach Artist?",
             "Tracks belong to albums and albums to artists. The database is normalised, so each fact is stored once and you join to combine them."),
    "S-24": ("What is a risk with NOT IN, and how else could you write it?",
             "If the subquery returns a NULL, NOT IN returns no rows. A LEFT JOIN with WHERE il.TrackId IS NULL avoids that."),
    "S-25": ("What happens with LIMIT 1 if two songs tie?",
             "One is returned arbitrarily. Look at the top rows or compare with a subquery on MAX to detect ties."),
    "S-26": ("Why does DESC matter here?",
             "ORDER BY sorts ascending by default, so without DESC you would get the slowest song."),
    "S-27": ("How do you get the third longest song reliably?",
             "Sort by duration descending and skip two rows: LIMIT 1 OFFSET 2."),
    "S-28": ("Why AND rather than OR?",
             "All three conditions must hold. With OR a song needs to meet only one, which gives 91 songs."),
    "S-29": ("Why round only at the end?",
             "Rounding in intermediate steps adds rounding error. Round the final figure for presentation."),
    "S-30": ("Why not hard-code Drake's artist_id?",
             "IDs can differ between databases or versions. Looking up the name keeps the query correct and readable."),
    "S-31": ("When is a JOIN better than a subquery?",
             "Both work here. A JOIN is clearer when you also want artist columns in the output; a subquery is simpler for a single filter."),
    "S-32": ("What could LIKE '%feat.%' miss?",
             "Other spellings such as \"ft.\" or \"featuring\". A text filter's result should be spot-checked."),
    "S-33": ("Is year a reliable column?",
             "It is IMDb's release year. It can be missing, or a planned future year, which matters for questions about recent movies."),
    "S-34": ("What would you do if the query returned two Johnny Depps?",
             "Use another attribute, such as birth year or film credits, to identify the right person. Names are never safe identifiers."),
    "S-35": ("Why can year be in the future?",
             "IMDb lists announced movies with their planned release year. The question explicitly includes them."),
    "S-36": ("Why does the boundary at exactly 9.0 matter?",
             "Hundreds of movies are rated exactly 9.0. Greater than excludes them; including them gives 1,890."),
    "S-37": ("\"Toy Story 3 in Real Life\" is in your result. Is that a problem?",
             "Not for this question: the stated rule counts every title starting with Toy Story. It shows how a rule-based filter can include records a human would exclude."),
    "S-38": ("Why join ratings to movies?",
             "The year is in movies and the rating in ratings. The join filters the ratings to 2013 movies."),
    "S-39": ("Why does the join reduce the number of 2011 movies?",
             "An inner join keeps only movies with a rating, which is exactly what the question asks."),
    "S-40": ("Why does the title need two apostrophes in SQL?",
             "A single quote ends a text value, so a quote inside the text is escaped by doubling it."),
    "S-41": ("Why DISTINCT here?",
             "A person who starred in several 2003 movies would otherwise be counted once per movie."),
    "S-42": ("Why is directors a separate table?",
             "A movie can have several directors and a person can direct several movies: a many-to-many relationship needs a linking table."),
    "S-43": ("Two movies share the top rating. How would you list both?",
             "Filter with WHERE rating = (SELECT MAX(...)) instead of LIMIT 1, which would hide the tie."),
    "S-44": ("Why not WHERE name = 'Johnny Depp' AND name = 'Helena Bonham Carter'?",
             "One row cannot hold two names at once. You need the set of movies for each person and their intersection."),
    "S-45": ("Why the condition birth = 1958?",
             "Several people are named Kevin Bacon. The birth year identifies the right one."),
    "S-46": ("Walk me through how each clue narrowed down the suspects.",
             "The interviews give four clues: leaving the courthouse lot 10:15 to 10:25, withdrawing at the Fifer Street ATM, a call under one minute, and the earliest flight the next morning. Each clue is a subquery; only Ernest satisfies all four."),
    "S-47": ("Why order by hour and minute?",
             "The flights table stores the time in separate columns, so you sort on both to find the first departure on 29 July."),
    "S-48": ("How do you know who was on the other end of the call?",
             "The thief was the caller. Joining the receiver's phone number back to people gives the accomplice."),
    "S-49": ("Why is this total a useful starting point in an audit?",
             "It is a control total: reconcile it with the source system to confirm the data is complete before testing."),
    "S-50": ("The control limit is $5,000. Why does this question use >= ?",
             "It defines the population as 5,000 or more. The control test itself (S-63) uses > 5,000, because exactly $5,000 is allowed."),
    "S-51": ("Why are returns negative, and why keep the sign?",
             "Refunds reduce spending, so they are recorded as negative amounts. Keeping the sign shows that the figure is a reduction."),
    "S-52": ("Why can grouping on FullName be risky?",
             "Names are not unique identifiers and capitalisation varies (C STOVER and C Stover), so one person can be split or two people merged."),
    "S-53": ("Why HAVING COUNT(*) > 10 and not WHERE?",
             "The count only exists after grouping, so it is filtered with HAVING."),
    "S-54": ("Why is the condition SUM(Amount) < -1000?",
             "Returns are negative, so returning more than $1,000 means a sum below -1,000."),
    "S-55": ("Why LIKE '%amazon%' and not Vendor = 'Amazon.com'?",
             "Amazon appears under several vendor names, such as Amazon.com and AMAZON MKTPLACE PMTS, and the question says Amazon anywhere in the name."),
    "S-56": ("Why is the tax avoided only an estimate?",
             "It assumes every purchase would have been taxed in Oklahoma. Out-of-state purchases and exempt items would not have been."),
    "S-57": ("How do you translate \"$1,000 or more\" into a condition on negative returns?",
             "Amount <= -1000. A larger return is a more negative number, so the comparison flips."),
    "S-58": ("Why does the subquery also need WHERE Year = 2014?",
             "You compare with the 2014 average. Without the filter the average covers all years."),
    "S-59": ("Why join two yearly subqueries rather than use one GROUP BY?",
             "Each vendor needs its 2013 and 2014 totals side by side, and the inner join keeps only vendors with purchases in both years."),
    "S-60": ("Why multiply by 100.0 rather than 100?",
             "With whole numbers SQLite does integer division, which cuts off the decimals. 100.0 forces a decimal result."),
    "S-61": ("Is spending above $50,000 automatically a control violation?",
             "No. Some cards may have approved higher limits. These are exceptions to investigate, not proven violations."),
    "S-62": ("Why GROUP BY FullName, Month and not just Month?",
             "The control applies per cardholder per month. Grouping by month alone measures the whole university."),
    "S-63": ("Why > 5000 and not >= 5000?",
             "The policy forbids spending more than $5,000 per transaction, so exactly $5,000 is allowed."),
    "S-64": ("Why require COUNT(*) > 1?",
             "A split purchase needs at least two swipes. A single transaction over $5,000 is a different violation, tested in S-63."),
    "S-65": ("What would be a false positive in this test, and how would you check it?",
             "Two colleagues buying from a large vendor on the same day for unrelated needs. Check receipts and business purpose before calling it a split."),
    "S-66": ("Why is a split between vendors harder to prove than a split between swipes?",
             "Different vendors usually means different goods. You need receipts showing that one known need was divided to stay under the limit."),
    "S-67": ("Why look for food purchases on the same day as a hotel purchase?",
             "A hotel purchase indicates travel status, and food while travelling must be claimed through the per diem, not the P-card."),
    "S-68": ("Benford's law expects 30.1% for digit 1 and you found 29.5%. What do you conclude?",
             "The distribution is close to Benford, so there is no sign of widespread manipulation. Benford's law is a risk indicator, not proof; look closer at the digits that deviate most."),
    "S-69": ("Why are these only possible duplicates?",
             "Buying the same item twice on one day can be legitimate. They are candidates to check against receipts and bank statements."),
    "S-70": ("Why count duplicate groups per person rather than lines?",
             "Otherwise one purchase charged three times would weigh as much as three separate incidents. Groups measure how often it happens."),
    "S-71": ("Why can round amounts indicate fraud?",
             "Real purchases with tax, shipping or unit prices rarely end in 000. Invented amounts often do."),
    "S-72": ("Which count would you use for a cardholder analysis, and why?",
             "Usually the case-insensitive one, after checking that the merged names really are the same person, documented as a transformation step."),
}
