# Resumo da Estrutura

## Campos de nível raiz
- `symbol`: Nome do ativo/símbolo (ex.: `"#WING-T"`).
- `date`: Data local associada aos dados, no formato ISO `YYYY-MM-DD` (ex.: `"2025-12-17"`).
- `timeframe`: Timeframe das barras (ex.: `"M1"` = 1 minuto).
- `bar`: Objeto com os campos da barra OHLC e metadados.

## Campos dentro de `bar`
- `time`: *Epoch seconds* (inteiro) — número de segundos desde `1970-01-01` UTC.  
  Converta com `datetime.fromtimestamp(time, timezone.utc)` para obter um timestamp legível.
- `open`: Preço de abertura da barra (`float`).
- `high`: Preço máximo na barra (`float`).
- `low`: Preço mínimo na barra (`float`).
- `close`: Preço de fechamento da barra (`float`).
- `tick_volume`: Contagem de ticks (número de alterações/quotes) durante a barra (`int`).
- `spread`: Spread observado durante a barra; a unidade depende do feed/broker (normalmente pontos/“ticks”).
- `real_volume`: Volume real negociado (quando disponível; pode ser `0` se o feed não fornecer).

## Observações úteis
- `time` é UTC; se quiser hora local, converta para o fuso desejado.
- `tick_volume` não é o mesmo que `real_volume`: o primeiro conta ticks, o segundo é o volume negociado (dependente do broker).
- `spread` e `real_volume` podem variar muito entre corretoras e instrumentos — trate-os como metadados.

## Exemplos em Python

### Converter `time` para `datetime` (UTC)
```python
from datetime import datetime, timezone

dt = datetime.fromtimestamp(bar["time"], timezone.utc)
