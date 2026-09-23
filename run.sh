#!/bin/bash
# SysPulse — Script de inicialização rápida
# Uso: ./run.sh [--sudo] [opções extras]

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$SCRIPT_DIR/venv"
VENV_PY="$VENV_DIR/bin/python"
VENV_PIP="$VENV_DIR/bin/pip"
MAIN="$SCRIPT_DIR/syspulse/main.py"
REQUIREMENTS="$SCRIPT_DIR/syspulse/requirements.txt"

# ── 1. Verificar/criar venv ──
if [ ! -f "$VENV_PY" ]; then
    echo "📦 Venv não encontrada. Criando em $VENV_DIR ..."
    python3 -m venv "$VENV_DIR"
    if [ $? -ne 0 ]; then
        echo "❌ Erro ao criar venv. Verifique se python3-venv está instalado."
        exit 1
    fi
    echo "✅ Venv criada."
fi

# ── 2. Verificar/instalar dependências ──
"$VENV_PY" -c "import psutil; import rich; import pynvml" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "📦 Instalando dependências..."
    "$VENV_PIP" install -q -r "$REQUIREMENTS"
    if [ $? -ne 0 ]; then
        echo "❌ Erro ao instalar dependências."
        exit 1
    fi
    echo "✅ Dependências instaladas."
fi

# ── 3. Rodar SysPulse ──
if [ "$1" = "--sudo" ]; then
    shift
    echo "⚡ Rodando SysPulse com sudo (para dados de energia RAPL)..."
    sudo "$VENV_PY" "$MAIN" "$@"
else
    echo "⚡ Rodando SysPulse..."
    echo "💡 Dica: use './run.sh --sudo' para dados de energia (Intel RAPL)"
    "$VENV_PY" "$MAIN" "$@"
fi
