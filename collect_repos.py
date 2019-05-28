import pandas as pd
from github import BadCredentialsException
from github import Github
from github import GithubException
import sys
import os
import json
import operator
import time
import requests.exceptions
from connect import *

MIN_STARS = 50
MAX_RETRIES = 10

def should_filter(repo):
    try:
        return repo.archived or repo.fork or repo.stargazers_count < MIN_STARS
    except (GithubException, requests.exceptions.ReadTimeout) as ex:
        return True

def get_repo_row(df, repo_id):
    row_df = df[df.id == repo_id]
    if row_df.empty:
        return None
    else:
        return row_df.iloc[0]

def get_repos_wrapper(g, start_id):
    print('Requesting repos from id: {0}'.format(start_id))
    retries = 0
    while True:
        try:
            repos_list = g.get_repos(since=start_id)
            return repos_list
        except (GithubException, requests.exceptions.ReadTimeout) as ex:
            retries += 1
            if retries > MAX_RETRIES:
                return None
            time.sleep(10)

def get_repo_wrapper(repo):
    retries = 0
    while True:
        repo_line = []
        try:
            repo_line.append(repo.id)
            repo_line.append(repo.owner.login)
            repo_line.append(repo.name)
            repo_line.append(repo.stargazers_count)
            commit_activity = repo.get_stats_commit_activity()
            repo_line.append(0 if commit_activity == None else commit_activity[0].total)
            repo_line.append(repo.get_contributors().totalCount)
            repo_line.append('|'.join(repo.get_languages().keys()))
            repo_line.append('new')
            return repo_line
        except (GithubException, requests.exceptions.ReadTimeout) as ex:
            print('Caught exception {0} - retrying')
            retries += 1
            if retries > MAX_RETRIES:
                return None
            time.sleep(10)

def get_repositories(g, mode, query, start_id, number_of_repos):
    print('Collecting information from GitHub repositories...')

    if os.path.isfile('repos.csv'):
        repos_df = pd.read_csv('repos.csv')
        start_id = max(start_id, int(repos_df.iloc[-1].id))
    else:
        repos_df = pd.DataFrame(columns=['id', 'owner', 'name', 'stars', 'commits_last_year', 'contributors', 'languages', 'status'])
    
    i = 0
    count = 0

    if mode == 'search':
        repos_list = g.search_repositories(query=query)

    last_repo = start_id
    new_row_added = False
    while True:
        if mode == 'all':
            repos_list = get_repos_wrapper(g, last_repo)
        # for each repository
        for repo in repos_list:
            last_repo = repo.id
            if get_repo_row(repos_df, repo.id) is not None:
                continue
            count += 1
            if count % 20 == 0 and new_row_added:
                repos_df.to_csv('repos.csv',index=False)
                new_row_added = False
            if should_filter(repo):
                print('filtered...')
                continue
            print(repo.owner.login+'/'+repo.name)

            repo_row = get_repo_wrapper(repo)
            if repo_row != None:
                repos_df.loc[len(repos_df)] = repo_row
                new_row_added = True

            df_len = len(repos_df)
            print('Iterated over {0} repos, there are {1} repos in the CSV'.format(count, df_len))
            if df_len > number_of_repos:
                break
        repos_df.to_csv('repos.csv',index=False)
        last_repo += 1
        if len(repos_df) > number_of_repos or mode == 'search':
            break
    print('Process Finished! {0} repositories collected.'.format(len(repos_df)))

if len(sys.argv) != 4:
    print('Usage: collect_repos.py all <initPag> <n_repos>')
    print('   or  collect_repos.py search <search_str> <n_repos>')
    sys.exit(0)

g = connect_to_github('config.json')
mode = sys.argv[1]
get_repositories(g, mode, None, int(sys.argv[2]), int(sys.argv[3]))
