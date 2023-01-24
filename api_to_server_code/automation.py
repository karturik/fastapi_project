import json
import logging
import time
from concurrent.futures import ThreadPoolExecutor

import numpy as np
import pandas as pd
import requests
from sqlalchemy.orm import Session

from database import SessionLocal
from models import Entries

with open("automation_config.json") as f:
    j = json.load(f)
    TOLOKA_OAUTH_TOKEN = j["token"]
    active_pools = j["pools"]
URL_API = "https://toloka.yandex.ru/api/v1/"
HEADERS = {
    "Authorization": "OAuth %s" % TOLOKA_OAUTH_TOKEN,
    "Content-Type": "application/JSON",
}


def check_active_pools():
    logger = logging.getLogger(__name__)
    logger.info("Идет проверка пулов")
    db: Session = SessionLocal()
    try:
        df = db.query(Entries).filter(Entries.status == "In Progress").all()
        logger.info(f"Количество незаконченных тасков: {len(df)}")

        all_tasks_submitted = []
        for i in active_pools:
            url = URL_API + f"assignments/?status=SUBMITTED&limit=10000&pool_id={i}"
            all_tasks_submitted.extend(requests.get(url, headers=HEADERS).json()["items"])
        logger.info(f"Submitted tasks: {len(all_tasks_submitted)}")
        logger.debug(f"Submitting tasks: {all_tasks_submitted}")

        if len(all_tasks_submitted) == 0 and len(df) == 0:
            logger.info(f"Нет активных задач, пропуск цикла")
            return

        def get_tasks(pool_id, ar=None):
            if ar is None:
                ar = ['SUBMITTED', 'ACCEPTED', 'REJECTED']
            tasks = []
            for i in ar:
                url = URL_API + f"assignments/?status={i}&limit=10000&pool_id={pool_id}"
                accepted_tasks = requests.get(url, headers=HEADERS).json()
                tasks.extend(accepted_tasks['items'])
                while accepted_tasks['has_more']:
                    max_id = max(list(map(lambda x: x['id'], accepted_tasks['items'])))
                    url = URL_API + f"assignments/?status={i}&limit=10000&pool_id={pool_id}&sort=id&id_gt={max_id}"
                    accepted_tasks = requests.get(url, headers=HEADERS).json()
                    tasks.extend(accepted_tasks['items'])
            logger.info(f"Tasks at pool #{pool_id}: {len(tasks)}")
            return tasks

        all_tasks = []
        for i in active_pools:
            all_tasks.extend(get_tasks(i))
        logger.info(f"Количество тасков в толоке: {len(all_tasks)}")
        logger.debug(f"Таски в толоке: {all_tasks}")

        tasksik_all = []
        for task in all_tasks:
            for ii, tasksik in enumerate(task['tasks']):
                del tasksik['reserved_for']
                del tasksik['unavailable_for']
                tasksik['sku'] = tasksik['input_values']['sku']
                tasksik['query'] = tasksik['input_values']['query']
                tasksik['link'] = tasksik['input_values']['link']
                del tasksik['input_values']
                tasksik['relevance'] = int(task['solutions'][ii]['output_values']['relevance'])
                tasksik['main_task_id'] = task['id']
                tasksik['task_suite_id'] = task['task_suite_id']
                tasksik['user_id'] = task['user_id']
                tasksik['status'] = task['status']
                tasksik['reward'] = task['reward']
                tasksik['user_id'] = task['user_id']
                tasksik['user_id'] = task['user_id']
                tasksik['user_id'] = task['user_id']
                tasksik_all.append(tasksik)
        logger.debug(tasksik_all)
        logger.info(f"Количество тасксиков: {len(tasksik_all)}")
        for i in df:
            tasksik_id = i.toloka_task_id
            t = list(filter(lambda x: x['id'] == tasksik_id, tasksik_all))
            if len(t) > 0:
                i.overlap = t[0]['overlap']
                i.remaining_overlap = t[0]['remaining_overlap']
                i.ans = list(sorted([int(x['relevance']) for x in t])[::-1])
                i.count_tasksik = len(t)

        for i in df:
            if i.ans is not None:
                ans = i.ans
                if len(ans) == 3:
                    l = pd.Series(ans).value_counts()
                    if l.iloc[0] == 3:
                        i.status = "Done"
                        logger.debug(f"DONE: {i}")
                        i.res = l.index[0].item()
                if len(ans) == 5:
                    l = pd.Series(ans).value_counts()
                    # случай 5-1
                    if l.iloc[0] == 5:
                        i.status = "Done"
                        logger.debug(f"DONE: {i}")
                        i.res = l.index[0].item()
                    # случай 4-1
                    if l.iloc[0] == 4:
                        i.status = "Done"
                        logger.debug(f"DONE: {i}")
                        i.res = l.index[0].item()
                    # случай 3-2
                    if l.iloc[0] == 3:
                        i.status = "Done"
                        logger.debug(f"DONE: {i}")
                        i.res = l.index[0].item()
                    if l.iloc[0] == 2:
                        # случай 2-1-1-1
                        if l.iloc[1] == 1:
                            i.status = "Done"
                            logger.debug(f"DONE: {i}")
                            i.res = l.index[0].item()
                        # случай 2-2-1
                        else:
                            if l.index[0] == 1 and l.index[1] == 2:
                                i.status = "Done"
                                logger.debug(f"DONE: {i}")
                                i.res = 1
                            elif l.index[0] == 0 and l.index[1] == 2:
                                i.status = "Done"
                                logger.debug(f"DONE: {i}")
                                i.res = 1
                            elif l.index[0] == 0 and l.index[1] == 1:
                                i.status = "Done"
                                logger.debug(f"DONE: {i}")
                                i.res = 1
                            elif l.index[0] == 0 and l.index[1] == 1 and l.index[2] == 2:
                                i.status = "Done"
                                logger.debug(f"DONE: {i}")
                                i.res = 1
                            else:
                                continue
                    if l.iloc[0] == 4:
                        i.is_more = True
                    else:
                        i.is_more = False
        db.commit()

        to_accept = []
        to_reject = []
        in_progress = 0
        for i in all_tasks_submitted[:]:
            tasks = i['tasks']
            len_tasks = len(tasks)
            task_id = i['id']
            m = []
            for jj, j in enumerate(tasks):
                id_couples = j['id']
                if j['infinite_overlap']:
                    res = int(j['known_solutions'][0]['output_values']['relevance'])
                else:
                    res = db.query(Entries).filter(Entries.toloka_task_id == id_couples).all()
                    res = res[0].res if len(res) > 0 else None
                if res is None:
                    m.append(-1)
                else:
                    user_ans = int(i['solutions'][jj]['output_values']['relevance'])
                    if user_ans == res:
                        m.append(1)
                    else:
                        if j['infinite_overlap']:
                            is_more = 0
                        else:
                            is_more = db.query(Entries).filter(Entries.toloka_task_id == id_couples).all()
                            is_more = is_more[0].is_more if len(is_more) > 0 else None
                        if is_more == 1:
                            m.append(0)
                        else:
                            if abs(res - user_ans) > 1:
                                m.append(0)
                            else:
                                m.append(1)
            m = np.array(m)
            if sum(m == 1) == len_tasks:
                to_accept.append(task_id)
            if (sum(m == 1) != len_tasks) and (sum(m == -1) == 0):
                a = np.array(list(range(1, len_tasks + 1)))
                s = 'Ошибка в задании:'
                for r in a[m == 0]:
                    s += f' {r},'
                s = s[:-1]
                to_reject.append([task_id, s])
            if sum(m == -1) > 0:
                in_progress += 1
        logger.info('Принимаем: %d\nОтклоняем: %d\nВ прогрессе: %d' % (len(to_accept), len(to_reject), in_progress))
        logger.debug('Принимаем: %s\nОтклоняем: %s\nВ прогрессе: %s' % (to_accept, to_reject, in_progress))

        def accept_task(task__id):
            json_check = {"status": "ACCEPTED", "public_comment": "Задание принято"}
            url = URL_API + "assignments/%s" % task__id
            return requests.patch(url, headers=HEADERS, json=json_check)

        with ThreadPoolExecutor(3) as executor:
            list(executor.map(accept_task, to_accept[:]))

        def reject_task(task):
            json_check = {"status": "REJECTED", "public_comment": task[1]}
            url = URL_API + "assignments/%s" % task[0]
            return requests.patch(url, headers=HEADERS, json=json_check)

        with ThreadPoolExecutor(3) as executor:
            list(executor.map(reject_task, to_reject[:]))
        logger.info("Идет процесс обновления оверлапа у тасксиков до 5")
        df_none = list(filter(lambda x: x.ans is not None and len(set(x.ans)) > 1 and len(x.ans) == 3 and x.overlap == 3, df))
        logger.info(f"Не принято: {len(df_none)}")
        logger.debug(f"Не приянто: {df_none}")
        for i in df_none:
            TASK_id = i.toloka_task_id
            json_check = {"overlap": 5, "infinite_overlap": False}
            url = URL_API + f"tasks/{TASK_id}?open_pool=true"
            logger.info(requests.patch(url, headers=HEADERS, json=json_check).status_code)
    except Exception as e:
        logger.error(e)
    finally:
        db.close()
        logger.info("Процесс обновления остановлен")


def add_task_to_toloka():
    logger = logging.getLogger(__name__)
    logger.info("Идет процесс добавления Submitted тасков в толоку")
    db: Session = SessionLocal()
    try:
        submitted = db.query(Entries).filter(Entries.status == "Submitted").limit(5000).all()
        input_values = []
        for row in submitted:
            if row.submitted_by is None:
                continue
            pool = row.submitted_by.pool
            input_values.append((pool, row))
        if len(input_values) != 0:
            json_task = list(map(lambda t: {
                "pool_id": str(t[0]),
                "input_values": {
                    "sku": str(t[1].sku),
                    "link": t[1].link,
                    "query": t[1].query
                },
                "overlap": 3
            }, input_values))
            url = URL_API + "tasks?open_pool=true"
            response = requests.post(url, headers=HEADERS, json=json_task)
            status = response.status_code
            if status == 201:
                logger.info(f"Добавлено {len(input_values)}")
                for pair in zip(input_values, response.json()["items"].values()):
                    _, row = pair[0]
                    res = pair[1]
                    row.status = "In Progress"
                    row.toloka_task_id = res["id"]
                    row.count_tasksik = 0
                    row.overlap = res["overlap"]
                    row.remaining_overlap = res["remaining_overlap"]
                db.commit()
            else:
                logger.error(f"Неудачно добавлено {len(input_values)}. Статус {status}")
    except Exception as e:
        logger.error(e)
    finally:
        db.close()
        logger.info("Процесс добавления Submitted тасков в толоку закончен")


def timeit(f):
    start = time.time()
    f()
    end = time.time()
    return end - start


def main():
    logging.basicConfig(
        filename="logs/automation.txt",
        format='%(asctime)s,%(msecs)d %(name)s %(levelname)s %(message)s',
        datefmt='%H:%M:%S',
        level=logging.INFO
    )
    while True:
        total_time = timeit(check_active_pools) + timeit(add_task_to_toloka)
        time_to_sleep = 2 * 60 - total_time
        if time_to_sleep > 0:
            time.sleep(time_to_sleep)


if __name__ == "__main__":
    main()