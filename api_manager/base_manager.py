import requests
import logging
import os
log = logging.getLogger('base_manager')

class BaseManager:
    """
    Create and manage a crawler for an url
    """
    #region EXCEPTIONS

    class ManagerException(Exception):
        def __init__(self, name, message):
            self.name = name
            super().__init__(message)

        def __str__(self):
            return f"[{self.name}] " + super().__str__()

    class InvalidCredentialsException(ManagerException):
        def __init__(self, name):
            super().__init__(name, 'Username or Password incorrect')

    #endregion

    def __init__(self, name: str, url: str, username: str=None, password: str=None):
        """
        Initialize the manager and try to login with the given username/password
        raise an exception if the login/password doesn't allow connection on the url
        params:
            name: the manager name for logging error and info
            username: String: the username  to login (ex: admin)
            password: String: the password to login (ex: admin)
            url: String: the base url of the service (ex :https://eve.devsca.com/github/scality/ring/artifacts/builds)
        """
        self.name = name
        if url.endswith('/'):
            url = url[:-1]
        self.url = url
        self.username = username
        self.password = password
        self.session = requests.Session()
        if not self.auth():
            raise self.InvalidCredentialsException(self.name)

    def auth(self):
        """
        send a request to the url to test if the connection can be established
        keep in the session the username/password for futur connection if provided
        return : Bool: True if the connexion is a success, False otherwise
        """
        if self.username is not None and self.password is not None:
            self.session.auth = (self.username, self.password)
        auth_response = self.session.get(self.url + '/')
        if auth_response.status_code != 401:
            return True
        return False

    def get(self, ressource='', data={}, headers={},**kwargs):
        """
        perform a get on a ressource
        low level get
        params : ressource: String: the ressource to place after the url (ex : exemple.html)
                 data : the body of the request as a json
                 kwargs: dict: Other parameter to pass as a query string (ex: format='txt', date__gt='01/01/2020') (optionnal)
        return : Response: requests.Response: the response receive from the API
        raise: Manager.ManagerExeption: if the response status is != 200
        """
        if data:
            response = self.session.get(f'{self.url}/{ressource}', params=kwargs, json=data, headers=headers)
        else:
            response = self.session.get(f'{self.url}/{ressource}', params=kwargs, headers=headers)
        if response.status_code != 200:
            raise self.ManagerException(self.name,
                f'Impossible to fetch url :"{response.request.url}", got status code : {response.status_code}')
        return response
    
    def post(self, ressource, data=None, json=None, **kwargs):
        """
        perform a post on a ressource
        low level post
        json and data are mutually exclusives
        params : ressource: String: the ressource to place after the url (ex : exemple.html)
                 data: object: the raw data to put in the post body
                 json: object: json formatted data to put in the body (python dict for exemple)
                 kwargs: dict: Other parameter to pass as a query string (ex: format='txt', date__gt='01/01/2020') (optionnal)
        return : Response: requests.Response: the response receive from the API
        raise: Manager.ManagerExeption: if the response status is != 200
        """
        if json is not None and data is not None:
            raise self.ManagerException(self.name, 'invalid post : the data and json can\'t be set at the same time.')
        response = self.session.post(f'{self.url}/{ressource}', params=kwargs, data=data, json=json)
        if response.status_code != 200:
            raise self.ManagerException(self.name,
                f'Impossible to fetch url :"{response.request.url}", got status code : {response.status_code}')
        return response
