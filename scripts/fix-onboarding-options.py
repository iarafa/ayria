#!/usr/bin/env python3
"""Atualiza options dos atributos select/multiselect no banco"""
import subprocess
import json

# Options que faltam
OPTIONS = {
    "genero": [
        {"value": "feminino", "label": "Feminino"},
        {"value": "masculino", "label": "Masculino"},
        {"value": "nao_binario", "label": "Não-binário"},
        {"value": "outro", "label": "Outro"},
        {"value": "prefiro_nao_dizer", "label": "Prefiro não dizer"},
    ],
    "estado_civil": [
        {"value": "solteiro", "label": "Solteiro(a)"},
        {"value": "casado", "label": "Casado(a)"},
        {"value": "uniao_estavel", "label": "União estável"},
        {"value": "divorciado", "label": "Divorciado(a)"},
        {"value": "viuvo", "label": "Viúvo(a)"},
        {"value": "outro", "label": "Outro"},
    ],
    "principais_foco": [
        {"value": "carreira", "label": "Carreira / propósito profissional"},
        {"value": "relacionamentos", "label": "Relacionamentos"},
        {"value": "saude_mental", "label": "Saúde mental / emocional"},
        {"value": "espiritualidade", "label": "Espiritualidade"},
        {"value": "financas", "label": "Finanças"},
        {"value": "familia", "label": "Família"},
        {"value": "criatividade", "label": "Criatividade / expressão"},
        {"value": "autoconhecimento", "label": "Autoconhecimento"},
    ],
    "nivel_experiencia": [
        {"value": "iniciante_total", "label": "Iniciante total — primeira vez"},
        {"value": "ja_li", "label": "Já li livros / vi vídeos"},
        {"value": "pratico_regular", "label": "Pratico meditação ou terapia"},
        {"value": "avancado", "label": "Trabalho na área (terapeuta / coach)"},
    ],
}

print("Atualizando options nos attribute_definitions...")
for code, opts in OPTIONS.items():
    opts_json = json.dumps(opts)
    # SQL escape: aspas duplas
    opts_escaped = opts_json.replace("'", "''")
    sql = f"UPDATE attribute_definitions SET options = '{opts_escaped}'::jsonb WHERE code = '{code}';"
    r = subprocess.run(
        ["docker", "exec", "ayria-postgres", "psql", "-U", "ayria", "-d", "ayria", "-c", sql],
        capture_output=True, text=True
    )
    if "UPDATE 1" in r.stdout:
        print(f"  ✅ {code}: {len(opts)} options")
    else:
        print(f"  ❌ {code}: {r.stdout.strip()}")

# Mesma coisa na tabela onboarding_config (cópia denormalizada)
print()
print("Atualizando options na tabela onboarding_config...")
for code, opts in OPTIONS.items():
    opts_json = json.dumps(opts)
    opts_escaped = opts_json.replace("'", "''")
    sql = f"UPDATE onboarding_config SET options = '{opts_escaped}'::jsonb WHERE attribute_code = '{code}';"
    r = subprocess.run(
        ["docker", "exec", "ayria-postgres", "psql", "-U", "ayria", "-d", "ayria", "-c", sql],
        capture_output=True, text=True
    )
    if "UPDATE 1" in r.stdout:
        print(f"  ✅ {code}: options no onboarding_config")
    else:
        print(f"  ❌ {code}: {r.stdout.strip()}")

print()
print("=== Verificando ===")
r = subprocess.run(
    ["docker", "exec", "ayria-postgres", "psql", "-U", "ayria", "-d", "ayria", "-c",
     "SELECT step, attribute_code, question_type, jsonb_array_length(options) as opts FROM onboarding_config WHERE question_type IN ('select', 'multiselect') ORDER BY step;"],
    capture_output=True, text=True
)
print(r.stdout)