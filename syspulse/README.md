# ⚡ SysPulse — Monitor de Sistema para Terminal

Monitor de sistema em tempo real para terminal Linux, inspirado no **btop**, com suporte a múltiplas arquiteturas (Intel, RISC-V) e detecção automática de GPU.

## 🚀 Funcionalidades

| Módulo | O que monitora |
|:---|:---|
| **CPU** | Uso por core, frequência, temperatura, modelo, load average |
| **RAM** | Total, usado, livre, swap, cached, buffers |
| **GPU** | VRAM, utilização, temperatura, clock, fan (NVIDIA/AMD/Intel auto-detect) |
| **Discos** | Partições, espaço, I/O read/write por segundo |
| **USB** | Dispositivos conectados, velocidade, consumo de energia |
| **Energia** | Watts CPU (Intel RAPL), watts GPU (NVML), total estimado |
| **Latência** | System FPS, jitter, load avg, scheduler latency, detecção de gargalos |
| **Processos** | Ranking por CPU%/MEM%, PID, threads, RSS, status |

## 📦 Instalação

```bash
# Ativar venv (já criada no SSD)
source /home/matheus-covre-de-queiroz/projetos_ssd/syspulse_venv/bin/activate

# Ou instalar dependências manualmente
pip install psutil rich nvidia-ml-py
```

## ▶️ Uso

```bash
# Modo normal
python syspulse/main.py

# Com dados de energia (requer sudo para Intel RAPL)
sudo /home/matheus-covre-de-queiroz/projetos_ssd/syspulse_venv/bin/python syspulse/main.py

# Intervalo personalizado (2 segundos)
python syspulse/main.py --interval 2

# Ordenar processos por memória
python syspulse/main.py --sort mem

# Mostrar mais processos
python syspulse/main.py --processes 20
```

## ⌨️ Controles

| Tecla | Ação |
|:---|:---|
| `q` | Sair |
| `s` | Alternar ordenação (CPU ↔ MEM) |
| `r` | Forçar atualização |
| `Ctrl+C` | Sair |

## 🏗️ Arquitetura

```
syspulse/
├── main.py              # Entry point + loop principal
├── collectors/          # Camada de coleta de dados
│   ├── cpu.py           # CPU (Intel + RISC-V)
│   ├── memory.py        # RAM + Swap
│   ├── gpu.py           # GPU auto-detect (NVIDIA/AMD/Intel)
│   ├── disk.py          # Discos + I/O
│   ├── usb.py           # Dispositivos USB
│   ├── energy.py        # Consumo energético (RAPL + NVML)
│   ├── latency.py       # Latência + FPS do sistema
│   └── processes.py     # Top processos
├── ui/                  # Camada de apresentação
│   ├── theme.py         # Cores e estilos
│   ├── widgets.py       # Painéis individuais
│   └── dashboard.py     # Layout completo
└── utils/
    └── helpers.py       # Formatação de valores
```

## 📋 Requisitos

- Python 3.8+
- Linux (testado no Ubuntu/kernel 7.0)
- Terminal com suporte a cores (256 cores ou truecolor)
- GPU NVIDIA: driver com NVML (automático)
- Dados de energia: kernel 5.10+ requer sudo

## 🔧 Compatibilidade

- **Intel**: Suporte completo (CPU, RAPL energia, temperatura)
- **RISC-V**: Suporte adaptado (CPU info, sem RAPL)
- **NVIDIA GPU**: Suporte completo via NVML
- **AMD GPU**: Suporte via sysfs (amdgpu driver)
- **Intel iGPU**: Suporte básico via sysfs (i915)
- **Sem GPU**: Funciona sem problemas, painel mostra "N/A"
