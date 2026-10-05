# %%
from dotenv import find_dotenv, load_dotenv

load_dotenv(find_dotenv())

import kaggle_benchmarks as kbench

# %%
@kbench.task(name="dummy-test-task")
def dummy_test_task(llm):
    response = llm.prompt("What is 2 + 2?")
    kbench.assertions.assert_in("4", response, expectation="Should contain 4")

dummy_test_task.run(kbench.llm)
