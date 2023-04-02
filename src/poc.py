import requests
import uuid
import json
import datetime
import time
#import threading

# Fintech - Comdirect API
# Version: 0.0.1
# Authors: Deniz Sonsal, Steven Poggel
# Github: deniz617@github, sbpnlp@github
# Mail: deniz.sonsal@gmail.com,


# Sources used:
# https://github.com/keisentraut/python-comdirect-api/blob/master/comdirect_api/session.py
# https://kunde.comdirect.de/cms/media/comdirect_REST_API_Dokumentation.pdf


def virtual_photoTAN():
    # TODO
    pass


def virtual_mobileTAN():
    tan = input("Enter TAN: ")
    return tan


def virtual_mobilePushTAN():
    input("Press ENTER after confirming Mobile PUSH.")
    return "123456"


def timestamp():
    return datetime.datetime.now(time.timezone.utc).strftime("%Y%m%d%H%M%S%f")


class API_poc:
    def __init__(self):
        self.base_url = "https://api.comdirect.de/"
        self.client_id = "User_"    #TODO: Enter credentials
        self.client_secret = ""     #TODO: Enter credentials
        self.username = ""          #TODO: Enter credentials
        self.password = ""          #TODO: Enter credentials

    def GetAccessToken(self):
        # POST /api/oauth/token
        # client_id={0}&client_secret={1}&username={2}&password={3}&grant_type=password
        r = requests.post(self.base_url + "oauth/token",
                          f"client_id={self.client_id}&"
                          f"client_secret={self.client_secret}&"
                          f"username={self.username}&"
                          f"password={self.password}&"
                          f"grant_type=password", allow_redirects=False,
                          headers={
                              "Accept": "application/json",
                              "Content-Type": "application/x-www-form-urlencoded",
                          },
                          )
        if not r.status_code == 200:
            raise RuntimeError(f"GetAccessToken {r.status_code}")

        r = r.json()
        self.access_token = r["access_token"]
        self.refresh_token = r["refresh_token"]
        self.expires_in = r["expires_in"]
        self.customerId = r["kdnr"]
        self.businessPartnerId = r["bpid"]
        self.contactId = r["kontaktId"]
        return r

    def GetSesssionId(self):
        self.session_id = uuid.uuid4()
        # GET /api/session/clients/user/v1/sessions
        r = requests.get(self.base_url + "api/session/clients/user/v1/sessions", allow_redirects=False,
                         headers={
                             "Accept": "application/json",
                             "Authorization": f"Bearer {self.access_token}",
                             "x-http-request-info": f'{{"clientRequestId":{{"sessionId":"{self.session_id}",'
                             f'"requestId":"{timestamp()}"}}}}',
                         },
                         )
        if not r.status_code == 200:
            raise RuntimeError(f"GetSesssionId {r.status_code}")
        serverside_sessionId = r.json()[0]["identifier"]
        self.session_id = serverside_sessionId
        return serverside_sessionId

    def ValidateSession(self):
        # POST /api/session/clients/user/v1/sessions/{self.session_id}/validate
        r = requests.post(self.base_url + f"api/session/clients/user/v1/sessions/{self.session_id}/validate", allow_redirects=False,
                          headers={
                              "Accept": "application/json",
                              "Authorization": f"Bearer {self.access_token}",
                              "x-http-request-info": f'{{"clientRequestId":{{"sessionId":"{self.session_id}",'
                              f'"requestId":"{timestamp()}"}}}}',
                              "Content-Type": "application/json",
                          },
                          data=f'{{"identifier":"{self.session_id}","sessionTanActive":true,"activated2FA":true}}',
                          )
        if not r.status_code == 201:
            raise RuntimeError(f"ValidateSession::Validate {r.status_code}")

        auth_info = json.loads(r.headers["x-once-authentication-info"])
        challengeId = auth_info["id"]
        self.challengeId = challengeId
        challengeType = auth_info["typ"]
        self.tan = 0
        match challengeType:
            case "P_TAN":
                self.tan = virtual_photoTAN()
            case "M_TAN":
                self.tan = virtual_mobileTAN()
            case "P_TAN_PUSH":
                self.tan = virtual_mobilePushTAN()
            case _:
                print(f"Unknown challenge: {challengeType}")
                return

        # Validate TAN
        # PATCH /api/session/clients/user/v1/sessions/{sessionId}
        r = requests.patch(self.base_url + f"api/session/clients/user/v1/sessions/{self.session_id}", allow_redirects=False,
                           headers={
                               "Accept": "application/json",
                               "Authorization": f"Bearer {self.access_token}",
                               "x-http-request-info": f'{{"clientRequestId":{{"sessionId":"{self.session_id}",'
                               f'"requestId":"{timestamp()}"}}}}',
                               "Content-Type": "application/json",
                               "x-once-authentication-info": f'{{"id":"{self.challengeId}"}}',
                               "x-once-authentication": self.tan,
                           },
                           data=f'{{"identifier":"{self.session_id}","sessionTanActive":true,"activated2FA":true}}',
                           )
        # if not r.status_code == 200:
        #    raise RuntimeError(f"ValidateSession::PATCH {r.status_code}")
        self.session_id = r.json()["identifier"]

        # Final OAuth
        # POST /oauth/token
        r = requests.post(self.base_url + "oauth/token", allow_redirects=False,
                          headers={
                              "Accept": "application/json",
                              "Content-Type": "application/x-www-form-urlencoded",
                          },
                          data=f"client_id={self.client_id}&client_secret={self.client_secret}&"
                          f"grant_type=cd_secondary&token={self.access_token}",
                          )
        if not r.status_code == 200:
            raise RuntimeError(f"ValidateSession::OAuth {r.status_code}")

        oauth_result = r.json()
        self.access_token = oauth_result["access_token"]
        self.refresh_token = oauth_result["refresh_token"]
        self.expire_time = oauth_result["expires_in"]
        self.customerId = oauth_result["kdnr"]
        self.businessPartnerId = oauth_result["bpid"]
        self.contactId = oauth_result["kontaktId"]
        self.isDisconnected = False

        return oauth_result

    def KeepAlive(self):
        # TODO.
        pass

    def KeepAliveThread(self):
        while not self.isDisconnected:
            # Refresh every 9min == 540seconds == 540,000ms
            time.sleep(1000*540)
            self.KeepAlive()

    def Auth(self):
        self.GetAccessToken()
        self.GetSesssionId()
        self.ValidateSession()

        # Maybe start a keep-alive thread.
        # self.workerThread = threading.Thread(target=self.KeepAliveThread)
        # self.workerThread.start()

    # Now we can get accounts/balance/transactions
    def GetBalances(self):
        # GET /api/banking/clients/user/v1/accounts/balances?paging-first=0&paging-count=1000
        r = requests.get(self.base_url + "api/banking/clients/user/v1/accounts/balances?paging-first=0&paging-count=1000", allow_redirects=False,
                         headers={
                             "Accept": "application/json",
                             "Authorization": f"Bearer {self.access_token}",
                             "x-http-request-info": f'{{"clientRequestId":{{"sessionId":"{self.session_id}",'
                             f'"requestId":"{timestamp()}"}}}}',
                         },
                         )
        if r.status_code != 200:
            raise RuntimeError(f"GetBalances {r.status_code}")
        return r

    def GetTransactions(self, account_id):
        # GET /api/banking/v1/accounts/{account_id}/transactions?transactionDirection=CREDIT_AND_DEBIT&transactionState=BOTH
        r = requests.get(self.base_url + f"api/banking/v1/accounts/{account_id}/transactions?transactionDirection=CREDIT_AND_DEBIT&transactionState=BOTH", allow_redirects=False,
                         headers={
                             "Accept": "application/json",
                             "Authorization": f"Bearer {self.access_token}",
                             "x-http-request-info": f'{{"clientRequestId":{{"sessionId":"{self.session_id}",'
                             f'"requestId":"{timestamp()}"}}}}',
                         },
                         )
        if r.status_code != 200:
            raise RuntimeError(f"GetTransactions {r.status_code}")
        return r

    def printFormattedTransaction(self, transaction):
        bookingDate = transaction["bookingDate"]
        bookingStatus = transaction["bookingStatus"]
        amount = transaction["amount"]["value"]
        currency = transaction["amount"]["unit"]
        transactionType = transaction["transactionType"]["text"]
        # remittanceInfo = transaction["remittanceInfo"].strip()
        remittanceInfo = ""

        # print(transaction)
        print(
            f"[{bookingDate}][{bookingStatus}] {amount} {currency} | {transactionType} | {remittanceInfo}")

    def printTransactions(self, transactions):
        transactions = transactions.json()
        totalTransactions = transactions["values"]
        for i in range(0, len(totalTransactions)):
            self.printFormattedTransaction(transactions["values"][i])


###################################################################################################################
###################################################################################################################

if __name__ == "__main__":
    api = API_poc()
    print("Auth..")
    api.Auth()

    balances = api.GetBalances().json()
    accounts = balances["values"]
    # print(accounts)

    for i in range(0, len(accounts)):
        # print(accounts[i])
        account_id = accounts[i]["accountId"]
        account_name = accounts[i]["account"]["accountType"]["text"]
        account_iban = accounts[i]["account"]["iban"]
        account_bic = accounts[i]["account"]["bic"]
        account_avacash = accounts[i]["availableCashAmount"]
        account_amount = account_avacash["value"]
        account_currency = account_avacash["unit"]
        account_str = f"\"{account_name}\" - {account_iban} | {account_amount} {account_currency}"
        print(f"Account[{i}]: {account_str}")

        print("---------------------------------------------------")
        transactions = api.GetTransactions(account_id)
        api.printTransactions(transactions)
        print("===================================================")
