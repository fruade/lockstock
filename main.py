from asyncio import run
from logging import INFO, basicConfig
from os import getenv
from sys import stdout
from aiogram import Bot, Dispatcher, F
from aiogram.client.default import DefaultBotProperties
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.utils.keyboard import ReplyKeyboardBuilder
from aiogram.types import Message, KeyboardButton
from aiogram.enums import ParseMode
from openai import AsyncOpenAI


OPENAI_API_KEY = getenv("OPENAI_API_KEY")
BOT_API_TOKEN = getenv("BOT_API_TOKEN")
MODEL_AI = "gpt-4o"
INSTRUCTIONS = "You are a helpful assistant that creates interesting questions with numeric answers."

storage = MemoryStorage()
dp = Dispatcher(storage=storage)
client = AsyncOpenAI(api_key=OPENAI_API_KEY)


# Определение состояний
class GameStates(StatesGroup):
    waiting_for_question = State()
    first_hint = State()
    second_hint = State()

# Генерация вопроса с помощью OpenAI
async def generate_question():
    prompt = """
    Пиши всегда по русски, придумай интересный не простой вопрос, ответ на который - целое число.
    Например: "Сколько планет в Солнечной системе?" или "Сколько лет длилась Столетняя война?"
    Вопрос должен быть сложным, но ответ должен быть однозначным числом.
    """

    response = await client.responses.create(
        model=MODEL_AI,
        instructions=INSTRUCTIONS,
        input=prompt,
        max_output_tokens=100,
    )

    return response.output_text

# Генерация подсказки на основе вопроса
async def generate_hint(question, hint_number):
    prompt = f"""
    Вот вопрос: {question}
    Придумай подсказку номер {hint_number} к этому вопросу, которая поможет угадать правильный ответ, но не раскроет его полностью.
    Подсказка должна быть полезной, но не очевидной.
    """

    response = await client.responses.create(
        model=MODEL_AI,
        instructions=INSTRUCTIONS,
        input=prompt,
        max_output_tokens=100,
    )

    return response.output_text

# Обработчик команды /start
@dp.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    builder = ReplyKeyboardBuilder()
    builder.add(KeyboardButton(text="Новая игра"))
    await message.answer(
        "Привет! Это игра lockstock. Нажми 'Новая игра'.",
        reply_markup=builder.as_markup(resize_keyboard=True)
    )

# Обработчик кнопки "Новая игра"
@dp.message(F.text == "Новая игра")
async def next_question(message: Message, state: FSMContext):
    await message.answer("Генерирую вопрос...")
    question = await generate_question()

    await state.update_data(question=question)
    await state.set_state(GameStates.waiting_for_question)

    builder = ReplyKeyboardBuilder()
    builder.add(KeyboardButton(text="1ая подсказка"))
    await message.answer(
        f"Вопрос: {question}\n\nТеперь игроки делают ставки!",
        reply_markup=builder.as_markup(resize_keyboard=True)
    )

# Обработчик кнопки "1ая подсказка"
@dp.message(F.text == "1ая подсказка", GameStates.waiting_for_question)
async def first_hint(message: Message, state: FSMContext):
    data = await state.get_data()
    question = data.get('question')

    await message.answer("Генерирую первую подсказку...")
    hint = await generate_hint(question, 1)

    await state.update_data(hint1=hint)
    await state.set_state(GameStates.first_hint)

    builder = ReplyKeyboardBuilder()
    builder.add(KeyboardButton(text="2ая подсказка"))
    await message.answer(
        f"Первая подсказка: {hint}\n\nИгроки могут повысить ставки или пропустить.",
        reply_markup=builder.as_markup(resize_keyboard=True)
    )

# Обработчик кнопки "2ая подсказка"
@dp.message(F.text == "2ая подсказка", GameStates.first_hint)
async def second_hint(message: Message, state: FSMContext):
    data = await state.get_data()
    question = data.get('question')

    await message.answer("Генерирую вторую подсказку...")
    hint = await generate_hint(question, 2)

    await state.update_data(hint2=hint)
    await state.set_state(GameStates.second_hint)

    builder = ReplyKeyboardBuilder()
    builder.add(KeyboardButton(text="Новая игра"))
    await message.answer(
        f"Вторая подсказка: {hint}\n\nИгроки делают финальные ставки!",
        reply_markup=builder.as_markup(resize_keyboard=True)
    )

async def main() -> None:
    bot = Bot(token=BOT_API_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    await dp.start_polling(bot)


if __name__ == "__main__":
    basicConfig(level=INFO, stream=stdout)
    run(main())