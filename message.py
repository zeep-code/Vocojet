import asyncio
import json
import logging
import random
import time
import os
from typing import Callable, Dict, List, Tuple
from deepgram import DeepgramClient, PrerecordedOptions, FileSource

DG_KEY = "API-KEY"
AUDIO_FILE_PATH = "story.mp3"
TRANSCRIPT_FILE = "transcript.json"

class AIBenchRunner:
    def __init__(self, fn: Callable, load: int, seed: int = 42):
        self.fn = fn
        self.load = load
        self.ttft = []
        self.end_to_end_latency = []
        self.cold_start = 0
        self.failed_queries = 0
        self.prompt_queue = asyncio.Queue()
        self.results_queue = asyncio.Queue()
        random.seed(seed)

    async def __call__(self) -> Dict:
        self.cold_start = await self.check_coldstart(threshold=15)
        concurrent_requests = []
        for audio_data in self.prepare_prompts():
            await self.prompt_queue.put(audio_data)
        for _ in range(self.load):
            concurrent_requests.append(asyncio.create_task(self.compute_metrics()))
        await asyncio.gather(*concurrent_requests)
        await self.unpack_metrics()
        return self.as_dict()

    @property
    def itl(self) -> List[float]:
        return [
            (e2e_lat - ttft) / 1
            for e2e_lat, ttft in zip(
                self.end_to_end_latency,
                self.ttft,
            )
        ]

    @property
    def output_tks_per_sec(self) -> List[float]:
        return [1000 / i for i in self.itl]

    def as_dict(self) -> Dict:
        return {
            "load": self.load,
            "ttft": self.ttft,
            "e2e_latency": self.end_to_end_latency,
            "itl": self.itl,
            "cold_start": self.cold_start,
            "failed_queries": self.failed_queries,
        }

    async def unpack_metrics(self):
        while not self.results_queue.empty():
            req_result: dict = await self.results_queue.get()
            print(req_result)
            self.ttft.append(req_result["ttft"])
            self.end_to_end_latency.append(req_result["e2e_latency"])
            self.failed_queries += req_result["failed_queries"]
            self.results_queue.task_done()

    @staticmethod
    def _get_audio_data() -> bytes:
        if os.path.exists(AUDIO_FILE_PATH):
            with open(AUDIO_FILE_PATH, "rb") as audio_file:
                return audio_file.read()
        else:
            raise FileNotFoundError("Audio file not found")

    def prepare_prompts(self) -> List[bytes]:
        audio_data = self._get_audio_data()
        return [audio_data] * self.load

    async def compute_metrics(self) -> None:
        audio_data = await self.prompt_queue.get()
        completions = []
        metrics_dict = {}

        deepgram = DeepgramClient(DG_KEY)
        payload: FileSource = {"buffer": audio_data}
        options = PrerecordedOptions(model="nova-2", smart_format=True)

        start_time = time.perf_counter()
        try:
            result = deepgram.listen.prerecorded.v("1").transcribe_file(payload, options)
        except Exception as e:
            print(f"exception: {e}")
            metrics_dict["failed_queries"] = 1
            self.results_queue.put_nowait(metrics_dict)
            self.prompt_queue.task_done()
            return

        end_time = time.perf_counter()
        metrics_dict["failed_queries"] = 0

        content = result.to_dict()
        metrics_dict["ttft"] = (end_time - start_time) * 1000  # Adjust as needed
        metrics_dict["e2e_latency"] = (end_time - start_time) * 1000
        await self.results_queue.put(metrics_dict)
        self.prompt_queue.task_done()

    async def check_coldstart(self, threshold: float) -> float:
        deepgram = DeepgramClient(DG_KEY)
        audio_data = self._get_audio_data()
        payload: FileSource = {"buffer": audio_data}
        options = PrerecordedOptions(model="nova-2", smart_format=True)

        start_time = time.perf_counter()
        try:
            result = await deepgram.listen.prerecorded.v("1").transcribe_file(payload, options)
        except Exception as e:
            logging.warning("Run during cold start failed")
            return 0
        end_time = time.perf_counter()

        cold_start = end_time - start_time
        if cold_start > threshold:
            return cold_start
        return 0

    

# Example usage
async def main():
    runner = AIBenchRunner(fn=None, load=5)  # fn is not used in this context
    metrics = await runner()
    print(metrics)

if __name__ == "__main__":
    await main()
