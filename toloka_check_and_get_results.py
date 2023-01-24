import psycopg2
import toloka.client as toloka

HEADERS = {"Authorization": "OAuth %s" % OAUTH_TOKEN, "Content-Type": "application/JSON"}
toloka_client = toloka.TolokaClient(OAUTH_TOKEN, 'SANDBOX')

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

pool_id = 'pool_id'

team_count = {'0':'0', '5':'1-5','10':'6-10','20':'11-20','50':'21-50', 'max':'51+'}
site_access = {'ok':"Good. Page works and team found", 'broken':"Site don't work or it can't be opened",'foreign':"Site is in an unclear language (not Russian and not English)",'noteam':"Site works good, but there is no team page"}

df_toloka = toloka_client.get_assignments_df(pool_id, status = ['APPROVED', 'REJECTED'])

def toloka_team_find_task_create(company_page):
    task = toloka.Task(
        input_values={
            'teamPageURL': f'{company_page}'},
        pool_id='pool_id'
    )
    r = toloka_client.create_task(task=task, allow_defaults=True)
    print(r)

for company_page in df_toloka['INPUT:teamPageURL']:
    try:
        if df_toloka[df_toloka['INPUT:teamPageURL']==company_page]['ASSIGNMENT:status'].values[0] == 'APPROVED':
            site_quality = df_toloka[df_toloka['INPUT:teamPageURL']==company_page]['OUTPUT:siteQuality'].values[0]
            if site_quality == "ok":
                site_quality = "Good. Page works and team found"
                team_page_url = df_toloka[df_toloka['INPUT:teamPageURL'] == company_page]['OUTPUT:teamPageURL'].values[0]
                team_member_list = df_toloka[df_toloka['INPUT:teamPageURL'] == company_page]['OUTPUT:teamMemberList'].values[0]
                status = 'DONE'
                team_size = len(team_member_list)
                if team_size >= 1 and team_size <= 5:
                    team_size = '1-5'
                elif team_size >= 6 and team_size <= 10:
                    team_size = '6-10'
                elif team_size >= 11 and team_size <= 20:
                    team_size = '11-20'
                elif team_size >= 21 and team_size <= 50:
                    team_size = '21-50'
                elif team_size >= 51:
                    team_size = 'max'
            else:
                site_quality = site_access[site_quality]
                team_page_url = 'nan'
                team_member_list = 'nan'
                status = 'DONE'
                team_size = 'nan'
            q.execute(f'''UPDATE public.teams SET site_quality = '{site_quality}', team_page_url = '{team_page_url}', team_member_list = '{team_member_list}', team_size= '{team_size}', status = '{status}'  WHERE company_url = '{company_page}';''')
            conn.commit()
        elif df_toloka[df_toloka['INPUT:teamPageURL']==company_page]['ASSIGNMENT:status'].values[0] == 'REJECTED':
            toloka_team_find_task_create(company_page)
    except Exception as e:
        print(e)

conn.close()