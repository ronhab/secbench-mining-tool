from utils import *
from github import *

# connect to github
def connect_to_github(cf_filename):
    try:
        data = load_cf_file(cf_filename)
        # authentication for Github API
        g = Github(data['github']['username'], data['github']['token'])
        print('Succesfully connected to github!')
        return g
    except BadCredentialsException as ex:
        print('Error:', ex)
        exit('\nSomething went wrong, check your GitHub credentials on the config.json file.')
