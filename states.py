from aiogram.fsm.state import State, StatesGroup

class States(StatesGroup):
    waiting_for_cities = State()
