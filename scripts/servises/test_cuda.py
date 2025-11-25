from numba import cuda
import numpy as np
import time


print("CUDA доступна:", cuda.is_available())

if cuda.is_available():
    print("Имя устройства:", cuda.get_current_device().name)


@cuda.jit
def add_one(arr):
    i = cuda.grid(1)  # глобальный индекс потока (как номер "рабочего")
    if i < arr.size:
        arr[i] += 1    # увеличиваем элемент на 1

print("CUDA доступна:", cuda.is_available())

if not cuda.is_available():
    raise SystemExit("CUDA недоступна в Python. Проверь драйверы и установку CUDA.")

print('# ---------- ДАННЫЕ НА CPU ----------')
data = np.arange(10, dtype=np.int32)
print("Исходный массив (CPU):", data)

print('# ---------- КОПИРУЕМ НА GPU ----------')
d_data = cuda.to_device(data)

print('# ---------- ЗАПУСК ЯДРА НА GPU ----------')
threads_per_block = 32
blocks_per_grid = (data.size + threads_per_block - 1) // threads_per_block

add_one[blocks_per_grid, threads_per_block](d_data)

print('# ---------- КОПИРУЕМ РЕЗУЛЬТАТ С GPU НА CPU ----------')
result = d_data.copy_to_host()
print("Результат после GPU:", result)

print('# ---------- Новый тест ----------')

from numba import cuda
import numpy as np
import time

@cuda.jit
def add_arrays_gpu(a, b, out):
    i = cuda.grid(1)
    if i < a.size:
        out[i] = a[i] + b[i]

N = 10_000_000  # 10 миллионов элементов

a = np.random.rand(N).astype(np.float32)
b = np.random.rand(N).astype(np.float32)

print('# ---------- CPU ВАРИАНТ ----------')
t0 = time.perf_counter()
out_cpu = a + b
t1 = time.perf_counter()
print(f"CPU время: {t1 - t0:.4f} c")

print('# ---------- GPU ВАРИАНТ ----------')
d_a = cuda.to_device(a)
d_b = cuda.to_device(b)
d_out = cuda.device_array_like(a)

threads_per_block = 256
blocks_per_grid = (N + threads_per_block - 1) // threads_per_block

print('# ---------- “прогрев” (первый запуск чуть медленнее из-за компиляции) ----------')
add_arrays_gpu[blocks_per_grid, threads_per_block](d_a, d_b, d_out)
cuda.synchronize()

t0 = time.perf_counter()
add_arrays_gpu[blocks_per_grid, threads_per_block](d_a, d_b, d_out)
cuda.synchronize()  # ждём окончания вычислений на GPU
t1 = time.perf_counter()

out_gpu = d_out.copy_to_host()

print(f"GPU время ядра (без учёта копирования): {t1 - t0:.4f} c")

print('# ---------- ПРОВЕРЯЕМ КОРРЕКТНОСТЬ ----------')
max_diff = np.max(np.abs(out_cpu - out_gpu))
print("Максимальное расхождение CPU vs GPU:", max_diff)
