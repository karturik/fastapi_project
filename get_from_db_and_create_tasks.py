import psycopg2
import pandas as pd
import toloka.client as toloka

conn = psycopg2.connect("""
    host=host
    port=port
    sslmode=require
    dbname=dbname
    user=user
    password=password
    target_session_attrs=read-write
""")

q = conn.cursor()

q.execute(f"SELECT id, company_url FROM public.teams WHERE status = 'WAIT';")
team_find_df = pd.DataFrame(q.fetchall(), columns = ['id', 'company_url'])

def toloka_team_find_task_create(team_find_df):
    try:
        for company_url in team_find_df['company_url']:
            task = toloka.Task(
                input_values={'teamPageURL': f'{company_url}'},
                pool_id='1441749')

            r = toloka_client.create_task(task=task, allow_defaults=True)
            print(r)
            q.execute(f"UPDATE public.teams SET status = 'IN WORK' WHERE company_url = '{company_url}';")
            conn.commit()
    except Exception as e:
        print(e)

if not team_find_df.empty:
    # print(team_find_df)
    toloka_team_find_task_create(team_find_df)


conn.close()