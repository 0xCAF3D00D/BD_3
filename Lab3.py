import json
import re
import requests as rq
import pandas as pd

from bs4 import BeautifulSoup

output = "vac.csv"
URL = "https://api.hh.ru/"

def proc_description(desc: str):
    if not desc:
        return None, None, None, None

    regex = r"<p><strong>*?(%s).*?<\/strong><\/p>"
    con = [m.start() for m in re.finditer(regex % "Условия", desc)]
    req = [m.start() for m in re.finditer(regex % "Требования", desc)]
    dut = [m.start() for m in re.finditer(regex % "Обязанности", desc)]
    descp = [["con", con[0] if con else -1],
             ["req", req[0] if req else -1],
             ["dut", dut[0] if dut else -1]]
    descp = sorted(descp, key=lambda item: item[1])
    descf = conditions = requirements = duties = None

    for i in range(3):
        if not descf and descp[i][1] != -1:
            descf = desc[:descp[i][1]]
        descp[i][1] = desc[descp[i][1]: descp[i+1][1] if i < 2 else len(desc)-1] if descp[i][1] != -1 else None
        if descp[i][0] == "con":
            conditions = descp[i][1]
        if descp[i][0] == "req":
            requirements = descp[i][1]
        if descp[i][0] == "dut":
            duties = descp[i][1]

    if not descf:
        descf = desc

    return ''.join(BeautifulSoup(descf, "html.parser").findAll(text=True))\
               .encode('utf-8').decode("utf-8") if descf else None, \
           ''.join(BeautifulSoup(conditions, "html.parser").findAll(text=True))\
               .encode('utf-8').decode("utf-8") if conditions else None, \
           ''.join(BeautifulSoup(requirements, "html.parser").findAll(text=True))\
               .encode('utf-8').decode("utf-8") if requirements else None, \
           ''.join(BeautifulSoup(duties, "html.parser").findAll(text=True))\
               .encode('utf-8').decode("utf-8") if duties else None

def boundaries(df): 
    name = [x for x in globals() if globals()[x] is df][0]
    print(name, ':')
    print('\tMin: ', df['max_salary'].min())
    print('\tMax: ', df['max_salary'].max())
    print('\tCount: ', df['max_salary'].count() if name != 'df1' 
          else df['max_salary'].isna().sum())

def mediansplit(df):
    median_value = df['max_salary'].median()
    return df[df['max_salary'] <= median_value], df[df['max_salary'] > median_value]

def diff(df):
    import pytz
    from datetime import datetime
    parced_at = pytz.utc.localize(datetime.now())
    return df['published_at'].apply(lambda x: (parced_at - datetime.strptime(x, '%Y-%m-%dT%X%z')).days)

def skillsplit(df):
    temp_df = df[:]
    ks = df['key_skills'].astype(str).str.split('; |, ').apply(pd.Series, 1).stack()
    ks.index = ks.index.droplevel(-1)
    ks.name = 'key_skills'
    del temp_df['key_skills']
    return temp_df.join(ks.astype(str).str.lower())
	
def printall(df):
    # все возможные значения максимальной и минимальной зарплаты и количество вхождений каждой из них в группу
    print('MIN_SALARY_COUNTS:\n', df['min_salary'].astype(str).value_counts(), '\n') 
    print('MAX_SALARY_COUNTS:\n', df['max_salary'].astype(str).value_counts(), '\n')

    # все возможные названия вакансий и количество вхождений каждой из них в группу
    print('NAME_COUNTS:\n', df['name'].value_counts(), '\n') 

    # среднее, максимальное и минимальное количество дней, на протяжении которых размещена вакансия на сайте (от даты парсинга)
    days_diff = diff(df)
    print('DAYS_SINCE_PUBLISHED_MEAN: ', days_diff.mean())
    print('DAYS_SINCE_PUBLISHED_MAX: ', days_diff.max())
    print('DAYS_SINCE_PUBLISHED_MIN: ', days_diff.min(), '\n')

    # все возможные значения требуемого опыта работы и количество вхождений каждого из них в группу
    print('EXPERIENCE_COUNTS:\n', df['experience'].astype(str).value_counts(), '\n') 
    
    # все возможные значения типов занятости и количество вхождений каждого из них в группу
    print('EMPLOYMENT_COUNTS:\n', df['employment'].astype(str).value_counts(), '\n')

    # все возможные значения рабочего графика и количество вхождений каждого из них в группу
    print('SCHEDULE_COUNTS:\n', df['schedule'].astype(str).value_counts(), '\n')

    # набор уникальных ключевых навыков и количество вхождений каждого навыка в группу
    print('SKILLS_COUNTS:\n', skillsplit(df)['key_skills'].value_counts(), '\n')

df = pd.DataFrame(columns=[
    "id",
    "name",
    "city",
    "min_salary",
    "max_salary",
    "employer",
    "published",
    "experience",
    "employment",
    "schedule",
    "description",
    "duties",
    "requirements",
    "conditions",
    "key_skills"
])

# Парсинг вакансий с hh.ru
for page in range(20):
    response = rq.get(URL + "vacancies?page=%d&per_page=100" % page)
    if response.status_code != 200:
        continue
    for vacancy in json.loads(response.text)["items"]:
        response = rq.get(URL + "vacancies/%s" % vacancy["id"])
        if response.status_code != 200:
            continue
        response = json.loads(response.text)

        area = response.get("area")
        address = response.get("address")
        city = None
        if address:
            city = address.get("city")
        elif area:
            city = area.get("name")

        salary = response.get("salary")
        min_salary = max_salary = None
        if salary:
            min_salary = salary.get("from")
            max_salary = salary.get("to")

        employer = response.get("employer")
        if employer:
            employer = employer.get("name")

        experience = response.get("experience")
        if experience:
            experience = experience.get("name")

        employment = response.get("employment")
        if employment:
            employment = employment.get("name")

        schedule = response.get("schedule")
        if schedule:
            schedule = schedule.get("name")

        description, conditions, requirements, duties = proc_description(response.get("description"))

        key_skills = response.get("key_skills")
        if key_skills:
            key_skills = "; ".join([skill["name"] for skill in key_skills])
        if isinstance(key_skills, list) and not len(key_skills):
            key_skills = None

        df.loc[len(df)] = [
            response.get("id"),
            response.get("name"),
            city,
            min_salary,
            max_salary,
            employer,
            response.get("published_at"),
            experience,
            employment,
            schedule,
            description,
            duties,
            requirements,
            conditions,
            key_skills
        ]
		
df.to_csv(output)
df = df.sort_values(['max_salary', 'min_salary'])
	
dfhalf1, dfhalf2 = mediansplit(df)
df9, df10 = mediansplit(dfhalf2)
df8, df9 = mediansplit(df9)
df7, df8 = mediansplit(df8)
df5, df6 = mediansplit(dfhalf1)
df4, df5 = mediansplit(df5)
df3, df4 = mediansplit(df4)
df2, df3 = mediansplit(df3)
df1 = df[df['max_salary'].isnull()]
for i in range(10):
	boundaries(globals()['df%d' % (i + 1)])