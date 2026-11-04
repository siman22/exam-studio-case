"""
Builds js/interpretation.js: data interpretation exams based on synthetic
regressions. Each scenario simulates data with a fixed random seed, fits OLS,
and stores the output in the layout of Excel's Data Analysis > Regression.

Run from the repository root:   python tools/build_interpretation.py
Requires numpy and statsmodels.
"""
import json, os
import numpy as np
import statsmodels.api as sm

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def fit(y, X, names, ylabel):
    Xc = sm.add_constant(np.column_stack(X))
    m = sm.OLS(y, Xc).fit()
    ci = m.conf_int(0.05)
    k = len(names)
    n = int(m.nobs)
    rows = []
    for i, nm in enumerate(["Intercept"] + names):
        rows.append({"name": nm, "coef": float(m.params[i]), "se": float(m.bse[i]),
                     "t": float(m.tvalues[i]), "p": float(m.pvalues[i]),
                     "lo": float(ci[i][0]), "hi": float(ci[i][1])})
    ssr = float(m.ess); sse = float(m.ssr)
    return {
        "y": ylabel,
        "stats": {"multipleR": float(np.sqrt(m.rsquared)), "r2": float(m.rsquared),
                  "adjR2": float(m.rsquared_adj), "se": float(np.sqrt(m.mse_resid)), "n": n},
        "anova": {"reg": [k, ssr, ssr / k, float(m.fvalue), float(m.f_pvalue)],
                  "res": [n - k - 1, sse, sse / (n - k - 1)],
                  "tot": [n - 1, ssr + sse]},
        "coef": rows,
    }


def c(out, name, dp=4):
    """Coefficient as displayed (rounded the way the page shows it)."""
    for r in out["coef"]:
        if r["name"] == name:
            return round(r["coef"], dp)
    raise KeyError(name)


def p(out, name):
    return next(r["p"] for r in out["coef"] if r["name"] == name)


def num(v, tol): return {"type": "number", "value": round(v, 4), "tol": tol}
def wrong(v, tol, hint): return {"answer": num(v, tol), "hint": hint}
def choice(options, correct): return {"type": "choice", "options": options, "correct": correct}
def open_(model): return {"type": "open", "model": model}


def sig_choice(out, names):
    sig = [nm for nm in names if p(out, nm) < 0.05]
    opts = ["None of them"] + names + ["All of them"] if len(names) > 1 else ["Yes", "No"]
    if len(names) == 1:
        return choice(opts, "Yes" if sig else "No")
    if len(sig) == 0: right = "None of them"
    elif len(sig) == len(names): right = "All of them"
    elif len(sig) == 1: right = sig[0]
    else:
        right = " and ".join(sig)
        opts.insert(-1, right)
    return choice(opts, right)


exams = []
rng = np.random.default_rng(20260101)

# ---------------------------------------------------------------- R1 restaurant: temperature and game days
n = 312
tmax = rng.normal(64, 18, n).clip(15, 99)
game = np.zeros(n); game[rng.choice(n, 13, replace=False)] = 1
sales = 2550 + 9.2 * tmax + 1380 * game + rng.normal(0, 880, n)
o = fit(sales, [tmax, game], ["tmax", "gameDay"], "netTotal (daily sales, USD)")
pred = c(o, "Intercept") + c(o, "tmax") * 70 + c(o, "gameDay") * 1
exams.append({
    "id": "R1", "title": "Restaurant sales, weather and game days", "case": "restaurant",
    "scenario": "Bob owns Larry's Commissary near a university stadium. You regressed total daily net sales on the day's maximum temperature and whether a football game was played that day, using 312 days of 2018 data.",
    "variables": [["netTotal", "Total net sales for the day, in USD"], ["tmax", "Maximum temperature that day, in °F"],
                  ["gameDay", "1 if a university football game was played that day, 0 otherwise"]],
    "output": o,
    "questions": [
        {"prompt": "Predict daily net sales on a game day with a maximum temperature of 70 °F.", "answer": num(pred, max(5, abs(pred) * 0.003)), "unit": "USD",
         "explain": f"Intercept + tmax × 70 + gameDay × 1 = {c(o,'Intercept'):,.2f} + {c(o,'tmax'):,.4f} × 70 + {c(o,'gameDay'):,.2f} = {pred:,.2f}.",
         "mistakes": [wrong(pred - c(o, "gameDay"), 5, "You left out the gameDay coefficient. On a game day gameDay = 1, so add its coefficient."),
                      wrong(pred - c(o, "Intercept"), 5, "You left out the intercept. Every prediction starts from the intercept.")]},
        {"prompt": "Explain to Bob, in one or two sentences, what the coefficient on tmax means.", "answer": open_(
            f"Holding game days constant, each additional degree Fahrenheit is associated with about ${c(o,'tmax'):.2f} more daily sales. It is an association, not proof that warmth causes the extra sales."),
         "explain": "A good answer names the unit (one °F), the size, the direction, holds the other variable constant and avoids claiming causality."},
        {"prompt": "Which variables are statistically significant at the 5% level?", "answer": sig_choice(o, ["tmax", "gameDay"]),
         "explain": "Compare each P-value with 0.05. " + "; ".join(f"{nm}: p = {p(o,nm):.4f}" for nm in ["tmax", "gameDay"]) + "."},
        {"prompt": "What percentage of the variation in daily sales does the model explain? Round to one decimal.", "answer": num(o["stats"]["r2"] * 100, 0.06), "unit": "%",
         "explain": f"R Square = {o['stats']['r2']:.4f}, so the model explains {o['stats']['r2']*100:.1f}% of the variation.",
         "mistakes": [wrong(o["stats"]["r2"], 0.0006, "R Square is a share. Multiply by 100 to express it as a percentage."),
                      wrong(o["stats"]["adjR2"] * 100, 0.06, "That is Adjusted R Square. The share of variation explained is R Square.")]},
        {"prompt": "Bob wants to use this model to decide how many staff to schedule. How confident should he be in a prediction for a single day? Mention one reason.", "answer": open_(
            f"Not very. R² is only {o['stats']['r2']:.2f} and the standard error is about ${o['stats']['se']:,.0f}, so actual sales on a given day can easily differ from the prediction by more than $1,000. Only 13 game days support the gameDay estimate, and other drivers (weekday, season, holidays) are left out."),
         "explain": "Strong answers use the standard error or R² from the output to quantify uncertainty."},
    ]})

# ---------------------------------------------------------------- R2 restaurant: last year's sales and interaction
s364 = rng.normal(3200, 900, n).clip(800, 7000)
game = np.zeros(n); game[rng.choice(n, 13, replace=False)] = 1
sales = 950 + 0.62 * s364 + 120 * game + 0.42 * game * s364 + rng.normal(0, 520, n)
o = fit(sales, [s364, game, game * s364], ["netTotal_364", "gameDay", "gameDay_x_netTotal_364"], "netTotal (daily sales, USD)")
pred_ng = c(o, "Intercept") + c(o, "netTotal_364") * 3000
effect = c(o, "gameDay") + c(o, "gameDay_x_netTotal_364") * 4000
exams.append({
    "id": "R2", "title": "Restaurant sales with an interaction term", "case": "restaurant",
    "scenario": "To see whether game days matter more on days that were already busy, you regressed daily net sales on sales on the same weekday one year earlier (netTotal_364), gameDay, and their product.",
    "variables": [["netTotal", "Total net sales for the day, in USD"], ["netTotal_364", "Total net sales 364 days earlier (same weekday last year), in USD"],
                  ["gameDay", "1 if a football game was played that day, 0 otherwise"], ["gameDay_x_netTotal_364", "gameDay multiplied by netTotal_364"]],
    "output": o,
    "questions": [
        {"prompt": "Predict sales on a day without a game, when sales on the same day last year were $3,000.", "answer": num(pred_ng, max(5, pred_ng * 0.003)), "unit": "USD",
         "explain": f"On non-game days both gameDay terms are zero: {c(o,'Intercept'):,.2f} + {c(o,'netTotal_364'):.4f} × 3,000 = {pred_ng:,.2f}.",
         "mistakes": [wrong(pred_ng - c(o, "Intercept"), 5, "You left out the intercept. Every prediction starts from the intercept.")]},
        {"prompt": "By how much does a game day change predicted sales when last year's sales on that day were $4,000?", "answer": num(effect, max(5, abs(effect) * 0.004)), "unit": "USD",
         "explain": f"Game-day effect = gameDay + interaction × netTotal_364 = {c(o,'gameDay'):,.2f} + {c(o,'gameDay_x_netTotal_364'):.4f} × 4,000 = {effect:,.2f}.",
         "mistakes": [wrong(c(o, "gameDay"), 1, "That is only the gameDay coefficient. With an interaction, the game-day effect also includes interaction × netTotal_364."),
                      wrong(c(o, "gameDay_x_netTotal_364") * 4000, 5, "You used only the interaction term. Add the gameDay coefficient as well.")]},
        {"prompt": "Explain the interaction coefficient to Bob in plain language.", "answer": open_(
            f"Game days add more to sales on days that were already busy. For every extra $1 of sales on the same day last year, a game day adds about ${c(o,'gameDay_x_netTotal_364'):.2f} on top of the normal game-day effect."),
         "explain": "The interaction says the effect of one variable depends on the level of the other."},
        {"prompt": "The gameDay coefficient on its own is not significant. Does that mean game days do not affect sales?", "answer": choice(
            ["Yes, game days have no effect", "No, its meaning changed: it is the game-day effect when netTotal_364 is zero",
             "No, because R Square is high"], "No, its meaning changed: it is the game-day effect when netTotal_364 is zero"),
         "explain": f"With an interaction, the gameDay coefficient (p = {p(o,'gameDay'):.3f}) is the effect at netTotal_364 = 0, a day that never occurs. The interaction (p = {p(o,'gameDay_x_netTotal_364'):.4f}) carries the game-day effect."},
        {"prompt": "What is the Adjusted R Square? Round to three decimals.", "answer": num(o["stats"]["adjR2"], 0.0006), "unit": "",
         "explain": f"Read it from Regression Statistics: {o['stats']['adjR2']:.4f}.",
         "mistakes": [wrong(o["stats"]["r2"], 0.0006, "That is R Square. Adjusted R Square is the row below it.")]},
    ]})

# ---------------------------------------------------------------- R3 IntegrateCo payroll
n = 480
reg = rng.uniform(40, 176, n)
ot = np.where(rng.random(n) < 0.35, rng.gamma(2, 4, n), 0)
loc2 = (rng.random(n) < 0.55).astype(float)
wages = 120 + 31.5 * reg + 47.0 * ot + 360 * loc2 + rng.normal(0, 420, n)
o = fit(wages, [reg, ot, loc2], ["RegHours", "OTHours", "Location2"], "GrossWages (per employee per month, USD)")
pred = c(o, "Intercept") + c(o, "RegHours") * 160 + c(o, "OTHours") * 10 + c(o, "Location2") * 0
premium = c(o, "OTHours") - c(o, "RegHours")
exams.append({
    "id": "R3", "title": "IntegrateCo payroll by hours and location", "case": "integrateco",
    "scenario": "Noah, IntegrateCo's CFO, asks what drives monthly gross wages. You regressed each employee's monthly gross wages on regular hours, overtime hours and work location (480 employee-months).",
    "variables": [["GrossWages", "Gross wages for the employee in the month, in USD"], ["RegHours", "Regular hours worked in the month"],
                  ["OTHours", "Overtime hours worked in the month"], ["Location2", "1 if the employee works at location 2, 0 for location 1"]],
    "output": o,
    "questions": [
        {"prompt": "Predict monthly gross wages for an employee at location 1 with 160 regular hours and 10 overtime hours.", "answer": num(pred, max(5, pred * 0.003)), "unit": "USD",
         "explain": f"{c(o,'Intercept'):,.2f} + {c(o,'RegHours'):.4f} × 160 + {c(o,'OTHours'):.4f} × 10 + {c(o,'Location2'):,.2f} × 0 = {pred:,.2f}.",
         "mistakes": [wrong(pred + c(o, "Location2"), 5, "You added the Location2 coefficient. The employee works at location 1, so Location2 = 0."),
                      wrong(pred - c(o, "Intercept"), 5, "You left out the intercept. Every prediction starts from the intercept.")]},
        {"prompt": "According to the model, how much more does an overtime hour cost than a regular hour?", "answer": num(premium, 0.02), "unit": "USD per hour",
         "explain": f"OTHours − RegHours = {c(o,'OTHours'):.4f} − {c(o,'RegHours'):.4f} = {premium:.2f}.",
         "mistakes": [wrong(c(o, "OTHours"), 0.02, "That is what an overtime hour costs in total. The question asks how much more it costs than a regular hour: subtract the RegHours coefficient.")]},
        {"prompt": "Interpret the Location2 coefficient for Noah.", "answer": open_(
            f"For the same regular and overtime hours, employees at location 2 earn about ${c(o,'Location2'):,.0f} more per month than employees at location 1. Noah should check whether job mix or seniority explains the gap before concluding that location 2 overpays."),
         "explain": "A dummy coefficient is the difference relative to the omitted category (location 1), holding the other variables constant."},
        {"prompt": "Is the location difference statistically significant at the 5% level?", "answer": sig_choice(o, ["Location2"]),
         "explain": f"P-value for Location2 = {p(o,'Location2'):.4g}, compared with 0.05."},
        {"prompt": "What is the upper limit of the 95% confidence interval for OTHours? Round to two decimals.", "answer": num(next(r['hi'] for r in o['coef'] if r['name']=='OTHours'), 0.006), "unit": "USD per hour",
         "explain": "Read Upper 95% in the OTHours row. The true effect of one overtime hour plausibly lies between Lower 95% and Upper 95%.",
         "mistakes": [wrong(next(r['lo'] for r in o['coef'] if r['name']=='OTHours'), 0.006, "That is the lower limit. The upper limit is in the Upper 95% column.")]},
    ]})

# ---------------------------------------------------------------- R4 P-card spending and fiscal year end
n = 360
holders = rng.integers(2, 40, n).astype(float)
june = (rng.random(n) < 1 / 12).astype(float)
limit = rng.normal(5, 1.5, n).clip(1, 10)
spend = 2100 + 1850 * holders + 9500 * june + 30 * limit + rng.normal(0, 7000, n)
o = fit(spend, [holders, june, limit], ["Cardholders", "June", "AvgLimit_k"], "MonthlySpend (department P-card spending, USD)")
pred = c(o, "Intercept") + c(o, "Cardholders") * 12 + c(o, "June") * 1 + c(o, "AvgLimit_k") * 5
exams.append({
    "id": "R4", "title": "P-card spending before fiscal year end", "case": "pcards",
    "scenario": "OSU's fiscal year ends on 30 June. Internal audit suspects departments spend remaining budgets on P-cards in June. You regressed monthly department P-card spending on the number of cardholders, a June indicator and the average single-transaction limit (360 department-months).",
    "variables": [["MonthlySpend", "Total P-card spending of the department in the month, in USD"], ["Cardholders", "Number of active cardholders in the department"],
                  ["June", "1 if the month is June (the last month of the fiscal year), 0 otherwise"], ["AvgLimit_k", "Average single-transaction limit of the department's cards, in thousands of USD"]],
    "output": o,
    "questions": [
        {"prompt": "Predict June spending for a department with 12 cardholders and an average limit of $5,000 (AvgLimit_k = 5).", "answer": num(pred, max(10, pred * 0.003)), "unit": "USD",
         "explain": f"{c(o,'Intercept'):,.2f} + {c(o,'Cardholders'):,.4f} × 12 + {c(o,'June'):,.2f} × 1 + {c(o,'AvgLimit_k'):,.4f} × 5 = {pred:,.2f}.",
         "mistakes": [wrong(pred - c(o, "June"), 10, "You left out the June coefficient. The question is about June, so June = 1."),
                      wrong(pred + c(o, "AvgLimit_k") * (5000 - 5), 10, "You entered the limit as 5,000. AvgLimit_k is measured in thousands, so $5,000 is 5.")]},
        {"prompt": "Which variables are statistically significant at the 5% level?", "answer": sig_choice(o, ["Cardholders", "June", "AvgLimit_k"]),
         "explain": "; ".join(f"{nm}: p = {p(o,nm):.4f}" for nm in ["Cardholders", "June", "AvgLimit_k"]) + "."},
        {"prompt": "What does the June coefficient suggest to an internal auditor, and what would you test next?", "answer": open_(
            f"Departments spend about ${c(o,'June'):,.0f} more in June than in other months with the same number of cardholders, which is consistent with spending leftover budget before year end. Next, test June transactions for split purchases, prohibited items and goods received after year end."),
         "explain": "Link the statistical result to a risk and to a concrete audit procedure."},
        {"prompt": "The AvgLimit_k coefficient is positive. Can you conclude that higher limits increase spending?", "answer": choice(
            ["Yes, the coefficient is positive", "No, the coefficient is not statistically different from zero", "Yes, because the F-test is significant"],
            "No, the coefficient is not statistically different from zero" if p(o, "AvgLimit_k") >= 0.05 else "Yes, the coefficient is positive"),
         "explain": f"p = {p(o,'AvgLimit_k'):.3f} and the 95% interval includes zero. A significant F-test only says the variables are jointly useful."},
        {"prompt": "What is the standard error of the regression (the typical size of a prediction error)? Round to the nearest dollar.", "answer": num(o["stats"]["se"], 1.0), "unit": "USD",
         "explain": f"Standard Error in Regression Statistics: {o['stats']['se']:,.2f}.",
         "mistakes": [wrong(o["anova"]["res"][2], 1.0, "That is MS Residual, the squared standard error. Take its square root, or read Standard Error under Regression Statistics.")]},
    ]})

# ---------------------------------------------------------------- R5 NYC film permits
n = 900
lead = rng.gamma(2.2, 2.1, n)
tv = (rng.random(n) < 0.58).astype(float)
weekend = (rng.random(n) < 0.22).astype(float)
hours = 14.2 + 0.18 * lead + 3.1 * tv - 1.6 * weekend + rng.normal(0, 4.2, n)
o = fit(hours, [lead, tv, weekend], ["LeadDays", "Television", "Weekend"], "DurationHours (permit duration, hours)")
pred = c(o, "Intercept") + c(o, "LeadDays") * 5 + c(o, "Television") * 0 + c(o, "Weekend") * 1
exams.append({
    "id": "R5", "title": "NYC film permit durations", "case": "nyc",
    "scenario": "The Mayor's Office wants to plan street closures. You regressed the duration of shooting permits on how many days in advance the permit was entered, whether the production is a television show and whether the shoot starts on a weekend (900 permits).",
    "variables": [["DurationHours", "Hours from StartDateTime to EndDateTime"], ["LeadDays", "Days between EnteredOn and StartDateTime"],
                  ["Television", "1 if Category is Television, 0 otherwise"], ["Weekend", "1 if the shoot starts on a Saturday or Sunday, 0 otherwise"]],
    "output": o,
    "questions": [
        {"prompt": "Predict the duration of a non-television shoot that starts on a weekend and was entered 5 days in advance. Round to one decimal.", "answer": num(pred, 0.06), "unit": "hours",
         "explain": f"{c(o,'Intercept'):.4f} + {c(o,'LeadDays'):.4f} × 5 + {c(o,'Television'):.4f} × 0 + {c(o,'Weekend'):.4f} × 1 = {pred:.2f}.",
         "mistakes": [wrong(pred - c(o, "Weekend"), 0.06, "You left out the Weekend coefficient. The shoot starts on a weekend, so Weekend = 1."),
                      wrong(pred + c(o, "Television"), 0.06, "You added the Television coefficient. This is not a television shoot, so Television = 0.")]},
        {"prompt": "Interpret the Weekend coefficient.", "answer": open_(
            f"Shoots starting on a weekend last about {abs(c(o,'Weekend')):.1f} hours {'less' if c(o,'Weekend')<0 else 'more'} than weekday shoots with the same lead time and category."),
         "explain": "Sign, size, unit and 'holding the other variables constant'."},
        {"prompt": "Which variables are statistically significant at the 5% level?", "answer": sig_choice(o, ["LeadDays", "Television", "Weekend"]),
         "explain": "; ".join(f"{nm}: p = {p(o,nm):.4g}" for nm in ["LeadDays", "Television", "Weekend"]) + "."},
        {"prompt": "What share of the variation in duration is left unexplained by the model? Round to one decimal.", "answer": num((1 - o["stats"]["r2"]) * 100, 0.06), "unit": "%",
         "explain": f"1 − R Square = 1 − {o['stats']['r2']:.4f} = {(1-o['stats']['r2'])*100:.1f}%.",
         "mistakes": [wrong(o["stats"]["r2"] * 100, 0.06, "That is the share the model explains. The unexplained share is 100% minus R Square.")]},
        {"prompt": "A planner says: \"Entering permits earlier makes shoots longer, so we should limit early applications.\" Respond.", "answer": open_(
            "The coefficient shows an association, not causation. Larger productions probably plan earlier and also shoot longer, so production size is an omitted variable. Limiting early applications would not shorten shoots."),
         "explain": "Look for omitted variables and reverse causality before acting on a coefficient."},
    ]})

# ---------------------------------------------------------------- R6 hotel revenue (ETL case 4 hotel)
n = 365
rooms = rng.integers(60, 240, n).astype(float)
conf = (rng.random(n) < 0.25).astype(float)
weekend = (rng.random(n) < 2 / 7).astype(float)
rev = 3200 + 118 * rooms + 4100 * conf + 150 * weekend + rng.normal(0, 2600, n)
o = fit(rev, [rooms, conf, weekend], ["OccupiedRooms", "ConferenceDay", "Weekend"], "DailyRevenue (hotel and food service, USD)")
pred = c(o, "Intercept") + c(o, "OccupiedRooms") * 150 + c(o, "ConferenceDay") * 1 + c(o, "Weekend") * 0
exams.append({
    "id": "R6", "title": "Hotel and conference center revenue", "case": "etl4",
    "scenario": "The controller of the hotel and conference center from the journal entry case wants to forecast daily revenue. You regressed daily revenue on occupied rooms, whether a conference was held and whether the day is a weekend (365 days).",
    "variables": [["DailyRevenue", "Revenue from rooms and food service for the day, in USD"], ["OccupiedRooms", "Number of occupied rooms that night"],
                  ["ConferenceDay", "1 if a conference was held that day, 0 otherwise"], ["Weekend", "1 if Saturday or Sunday, 0 otherwise"]],
    "output": o,
    "questions": [
        {"prompt": "Predict revenue on a weekday conference day with 150 occupied rooms.", "answer": num(pred, max(10, pred * 0.003)), "unit": "USD",
         "explain": f"{c(o,'Intercept'):,.2f} + {c(o,'OccupiedRooms'):.4f} × 150 + {c(o,'ConferenceDay'):,.2f} × 1 + {c(o,'Weekend'):,.2f} × 0 = {pred:,.2f}.",
         "mistakes": [wrong(pred - c(o, "ConferenceDay"), 10, "You left out the ConferenceDay coefficient. It is a conference day, so ConferenceDay = 1.")]},
        {"prompt": "How much extra revenue is associated with one more occupied room? Round to two decimals.", "answer": num(c(o, "OccupiedRooms"), 0.006), "unit": "USD",
         "explain": "Read the OccupiedRooms coefficient.",
         "mistakes": [wrong(next(r['se'] for r in o['coef'] if r['name']=='OccupiedRooms'), 0.006, "That is the standard error of the coefficient. The effect itself is in the Coefficients column.")]},
        {"prompt": "Is the Weekend coefficient statistically significant at the 5% level?", "answer": sig_choice(o, ["Weekend"]),
         "explain": f"P-value = {p(o,'Weekend'):.3f}."},
        {"prompt": "What does Significance F tell the controller?", "answer": open_(
            f"Significance F ({o['anova']['reg'][4]:.2g}) is the p-value of the test that all slope coefficients are zero. It is far below 0.05, so the variables together explain revenue better than the average alone. It says nothing about any single variable."),
         "explain": "The F-test is a joint test of all slopes."},
        {"prompt": "The controller wants to forecast revenue for a day with 400 occupied rooms after a planned extension. What is the main risk of using this model?", "answer": open_(
            "Extrapolation: the data only covers 60 to 240 occupied rooms, so the linear relationship may not hold at 400 (e.g. extra staff, discounts for large groups)."),
         "explain": "Predictions far outside the range of the data are unreliable."},
    ]})

for e in exams:
    for i, q in enumerate(e["questions"]):
        for w in q.get("mistakes", []):
            a, b = q["answer"], w["answer"]
            assert abs(a["value"] - b["value"]) > a["tol"] + b["tol"], f"{e['id']} Q{i+1}: diagnosis overlaps the correct answer"

with open(os.path.join(ROOT, "js", "interpretation.js"), "w", encoding="utf-8") as f:
    f.write("// Generated by tools/build_interpretation.py.\n")
    f.write("window.INTERP = " + json.dumps(exams, ensure_ascii=False, indent=1) + ";\n")
print(f"Wrote {len(exams)} interpretation exams")
for e in exams:
    print(e["id"], {r["name"]: (round(r["coef"], 3), round(r["p"], 4)) for r in e["output"]["coef"]}, "R2", round(e["output"]["stats"]["r2"], 3))
    for q in e["questions"]:
        if q["answer"]["type"] == "choice": print("   choice ->", q["answer"]["correct"])
