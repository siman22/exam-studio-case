# Tickmark: exam practice for Data Analytics in Accounting

A static practice website for the oral exam in Data Analytics in Accounting (SDU). Students practise the two exam types they will receive:

- **Data manipulation exams** (12 exams, 135 questions): two Excel and two SQL questions per exam, built from the course cases: NYC film permits, ETL cases 1 to 4, IntegrateCo payroll, the restaurant regression case, Chinook, the CS50 songs, movies and Fiftyville databases, and the OSU P-card audit.
- **Data interpretation exams** (6 exams): an Excel-style regression output with questions on prediction, interpretation, significance and limitations. The regressions are synthetic but use scenarios and variables from the course cases.

Students download the files, solve each question in Excel or SQL, type their result and check it. Every question has a worked solution. Nothing is stored or sent; the site has no server.

## Improvement over the reference site: feedback that teaches

The reference site tells a student whether an answer is right. This site also tells them **why it is wrong**, and **asks them to explain it when it is right**.

- **Diagnosed mistakes (91).** When a wrong answer matches a typical mistake, for example forgetting to remove a duplicate row, matching on PreparerID without BusinessUnitID, using `>` where the control says "or more", or counting groups instead of lines, the student sees the likely cause. For SQL questions they can also see the query that produces their number. Every diagnosed value is produced by actually running the wrong method on the course data (`tools/feedback.py`). The build fails if a wrong method happens to give the correct answer, so a diagnosis can never be shown for a right answer.
- **Examiner follow-ups (135).** After a correct answer the student gets the question an oral examiner would ask ("Why HAVING and not WHERE?", "Why is PlantID alone not a unique identifier?"), writes or says an answer, compares it with a model answer and marks whether they could explain it. Exams count correct answers and explained answers separately.

## Files

```
index.html              page shell
css/style.css           design
js/app.js               routing, answer checking, timer
js/bank.js              question bank (generated, do not edit by hand)
js/interpretation.js    regression exams (generated)
data/                   datasets students download
tools/build_bank.py     source of all questions; validates SQL answers
tools/feedback.py       diagnosed mistakes and examiner follow-ups (improvement)
tools/build_interpretation.py   generates the regression exams
```

## Run it locally

Open a terminal in this folder and run:

```
python -m http.server 8000
```

Then open http://localhost:8000. (Opening index.html directly also works.)

## Publish on GitHub Pages

1. Create a new public repository on GitHub, for example `exam-practice`.
2. Upload this folder with GitHub Desktop or VS Code (Source Control > Publish). The browser upload on github.com does not accept files over 25 MB, and `data/sql/movies.db.zip` is 39 MB.
3. In the repository, go to Settings > Pages, choose "Deploy from a branch", select `main` and `/ (root)`, and save.
4. After a minute the site is live at `https://<username>.github.io/exam-practice/`.

## Changing questions

Edit `tools/build_bank.py`, then run:

```
pip install statsmodels numpy
python tools/build_bank.py
```

The script re-runs every SQL solution against the real databases and refuses to write `js/bank.js` if any stored answer no longer matches its query. It also checks that every exam refers to existing questions and every dataset file exists.

## Assumptions to revisit

- Each data manipulation exam has two Excel and two SQL questions with a suggested time of 20 minutes; interpretation exams suggest 10 minutes. Both values are at the top of `js/app.js`.
- For P-card questions, FullName is used exactly as stored. Question S-72 shows why this matters: names appear in different capitalisation.
- Answers in the official PwC keys were reproduced and verified. One key answer (albums downloaded in full: 49) could not be reproduced and was replaced by an unambiguous question (S-21).
