"""Account manager module """
import re
import json
from datetime import datetime, timezone
from uc3m_money.account_management_exception import AccountManagementException
from uc3m_money.account_management_config import (TRANSFERS_STORE_FILE,
                                        DEPOSITS_STORE_FILE,
                                        TRANSACTIONS_STORE_FILE,
                                        BALANCES_STORE_FILE)

from uc3m_money.transfer_request import TransferRequest
from uc3m_money.account_deposit import AccountDeposit


class AccountManager:
    """Class for providing the methods for managing the orders"""
    def __init__(self):
        pass


    def validate_iban(self, iban: str):
        """
    Calcula el dígito de control de un IBAN español.

    Args:
        iban (str): El IBAN sin los dos últimos dígitos (dígito de control).

    Returns:
        str: El dígito de control calculado.
        """

        if not self.check_regex(r"^ES[0-9]{22}", iban):
            raise AccountManagementException("Invalid IBAN format")
        original_code = iban[2:4]
        #replacing the control
        iban = iban[:2] + "00" + iban[4:]
        iban = iban[4:] + iban[:4]


        # Convertir el IBAN en una cadena numérica, reemplazando letras por números
        iban = (iban.replace('A', '10').replace('B', '11').
                replace('C', '12').replace('D', '13').replace('E', '14').
                replace('F', '15'))
        iban = (iban.replace('G', '16').replace('H', '17').
                replace('I', '18').replace('J', '19').replace('K', '20').
                replace('L', '21'))
        iban = (iban.replace('M', '22').replace('N', '23').
                replace('O', '24').replace('P', '25').replace('Q', '26').
                replace('R', '27'))
        iban = (iban.replace('S', '28').replace('T', '29').replace('U', '30').
                replace('V', '31').replace('W', '32').replace('X', '33'))
        iban = iban.replace('Y', '34').replace('Z', '35')

        # Mover los cuatro primeros caracteres al final

        # Convertir la cadena en un número entero
        int_i = int(iban)

        # Calcular el módulo 97
        mod = int_i % 97

        # Calcular el dígito de control (97 menos el módulo)
        control_digit = 98 - mod

        if int(original_code) != control_digit:
            #print(control_digit)
            raise AccountManagementException("Invalid IBAN control digit")

        return iban

    @staticmethod
    def check_regex(pattern, string):
        """checks if string is in pattern"""
        mr = re.compile(pattern)
        res = mr.fullmatch(string)
        return res

    def validate_concept(self, concept: str):
        """regular expression for checking the minimum and maximum length as well as
        the allowed characters and spaces restrictions
        there are other ways to check this"""
        is_valid_concept = self.check_regex(r"^(?=^.{10,30}$)([a-zA-Z]+(\s[a-zA-Z]+)+)$", concept)
        if not is_valid_concept:
            raise AccountManagementException ("Invalid concept format")

    def validate_transfer_date(self, transfer_date):
        """validates the arrival date format  using regex"""
        is_valid_date = self.check_regex(r"^(([0-2]\d|3[0-1])\/(0\d|1[0-2])\/\d\d\d\d)$",
                                         transfer_date)
        if not is_valid_date:
            raise AccountManagementException("Invalid date format")

        try:
            my_date = datetime.strptime(transfer_date, "%d/%m/%Y").date()
        except ValueError as ex:
            raise AccountManagementException("Invalid date format") from ex

        if my_date < datetime.now(timezone.utc).date():
            raise AccountManagementException("Transfer date must be today or later.")

        if my_date.year < 2025 or my_date.year > 2050:
            raise AccountManagementException("Invalid date format")
        return transfer_date
    #pylint: disable=too-many-arguments
    def transfer_request(self, from_iban: str,
                         to_iban: str,
                         concept: str,
                         transfer_type: str,
                         date: str,
                         amount: float)->str:
        """first method: receives transfer info and
        stores it into a file"""
        self.validate_iban(from_iban)
        self.validate_iban(to_iban)
        self.validate_concept(concept)

        is_valid_transfer_type = self.check_regex(r"(ORDINARY|IMMEDIATE|URGENT)", transfer_type)
        if not is_valid_transfer_type:
            raise AccountManagementException("Invalid transfer type")
        self.validate_transfer_date(date)



        try:
            amount_float  = float(amount)
        except ValueError as exc:
            raise AccountManagementException("Invalid transfer amount") from exc

        amount_string = str(amount_float)
        if '.' in amount_string:
            decimals = len(amount_string.split('.')[1])
            if decimals > 2:
                raise AccountManagementException("Invalid transfer amount")

        if amount_float < 10 or amount_float > 10000:
            raise AccountManagementException("Invalid transfer amount")

        my_request = TransferRequest(from_iban=from_iban,
                                     to_iban=to_iban,
                                     transfer_concept=concept,
                                     transfer_type=transfer_type,
                                     transfer_date=date,
                                     transfer_amount=amount)

        try:
            with open(TRANSFERS_STORE_FILE, "r", encoding="utf-8", newline="") as file:
                transfer_list = json.load(file)
        except FileNotFoundError:
            transfer_list = []
        except json.JSONDecodeError as ex:
            raise AccountManagementException("JSON Decode Error - Wrong JSON Format") from ex

        for transfer_instance in transfer_list:
            if (transfer_instance["from_iban"] == my_request.from_iban and
                    transfer_instance["to_iban"] == my_request.to_iban and
                    transfer_instance["transfer_date"] == my_request.transfer_date and
                    transfer_instance["transfer_amount"] == my_request.transfer_amount and
                    transfer_instance["transfer_concept"] == my_request.transfer_concept and
                    transfer_instance["transfer_type"] == my_request.transfer_type):
                raise AccountManagementException("Duplicated transfer in transfer list")

        transfer_list.append(my_request.to_json())

        try:
            with open(TRANSFERS_STORE_FILE, "w", encoding="utf-8", newline="") as file:
                json.dump(transfer_list, file, indent=2)
        except FileNotFoundError as ex:
            raise AccountManagementException("Wrong file  or file path") from ex
        except json.JSONDecodeError as ex:
            raise AccountManagementException("JSON Decode Error - Wrong JSON Format") from ex

        return my_request.transfer_code

    def deposit_into_account(self, input_file:str)->str:
        """manages the deposits received for accounts"""
        try:
            with open(input_file, "r", encoding="utf-8", newline="") as file:
                i_d = json.load(file)
        except FileNotFoundError as ex:
            raise AccountManagementException("Error: file input not found") from ex
        except json.JSONDecodeError as ex:
            raise AccountManagementException("JSON Decode Error - Wrong JSON Format") from ex

        # comprobar valores del fichero
        try:
            deposit_iban = i_d["IBAN"]
            deposit_amount = i_d["AMOUNT"]
        except KeyError as e:
            raise AccountManagementException("Error - Invalid Key in JSON") from e


        deposit_iban = self.validate_iban(deposit_iban)
        is_valid_deposit_amount = (r"^EUR [0-9]{4}\.[0-9]{2}", deposit_amount)
        if not is_valid_deposit_amount:
            raise AccountManagementException("Error - Invalid deposit amount")

        deposit_amount_float = float(deposit_amount[4:])
        if deposit_amount_float == 0:
            raise AccountManagementException("Error - Deposit must be greater than 0")

        deposit_obj = AccountDeposit(to_iban=deposit_iban,
                                     deposit_amount=deposit_amount_float)

        try:
            with open(DEPOSITS_STORE_FILE, "r", encoding="utf-8", newline="") as file:
                deposit_list = json.load(file)
        except FileNotFoundError as ex:
            deposit_list = []
        except json.JSONDecodeError as ex:
            raise AccountManagementException("JSON Decode Error - Wrong JSON Format") from ex

        deposit_list.append(deposit_obj.to_json())

        try:
            with open(DEPOSITS_STORE_FILE, "w", encoding="utf-8", newline="") as file:
                json.dump(deposit_list, file, indent=2)
        except FileNotFoundError as ex:
            raise AccountManagementException("Wrong file  or file path") from ex
        except json.JSONDecodeError as ex:
            raise AccountManagementException("JSON Decode Error - Wrong JSON Format") from ex

        return deposit_obj.deposit_signature


    def read_transactions_file(self):
        """loads the content of the transactions file
        and returns a list"""
        try:
            with open(TRANSACTIONS_STORE_FILE, "r", encoding="utf-8", newline="") as file:
                input_list = json.load(file)
        except FileNotFoundError as ex:
            raise AccountManagementException("Wrong file  or file path") from ex
        except json.JSONDecodeError as ex:
            raise AccountManagementException("JSON Decode Error - Wrong JSON Format") from ex
        return input_list


    def calculate_balance(self, iban:str)->bool:
        """calculate the balance for a given iban"""
        iban = self.validate_iban(iban)
        t_l = self.read_transactions_file()
        iban_found = False
        balance_string = 0
        for transaction in t_l:
            #print(transaction["IBAN"] + " - " + iban)
            if transaction["IBAN"] == iban:
                balance_string += float(transaction["amount"])
                iban_found = True
        if not iban_found:
            raise AccountManagementException("IBAN not found")

        last_balance = {"IBAN": iban,
                        "time": datetime.timestamp(datetime.now(timezone.utc)),
                        "BALANCE": balance_string}

        try:
            with open(BALANCES_STORE_FILE, "r", encoding="utf-8", newline="") as file:
                balance_list = json.load(file)
        except FileNotFoundError:
            balance_list = []
        except json.JSONDecodeError as ex:
            raise AccountManagementException("JSON Decode Error - Wrong JSON Format") from ex

        balance_list.append(last_balance)

        try:
            with open(BALANCES_STORE_FILE, "w", encoding="utf-8", newline="") as file:
                json.dump(balance_list, file, indent=2)
        except FileNotFoundError as ex:
            raise AccountManagementException("Wrong file  or file path") from ex
        return True
