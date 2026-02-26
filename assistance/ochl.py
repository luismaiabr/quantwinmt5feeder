import MetaTrader5 as mt5
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo
import json
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

# Lista de símbolos candidatos
SYMBOL_CANDIDATOS = [
    "WINJ26"
]


def listar_simbolos_por_mascara(mask: str):
    """Lista símbolos que correspondem a uma máscara."""
    r = mt5.symbols_get(group=mask)
    if r is None:
        return []
    return [s.name for s in r]


def listar_simbolos_win():
    """Lista todos os símbolos WIN disponíveis."""
    masks = ["*WIN*", "*win*"]
    names = []
    for m in masks:
        names.extend(listar_simbolos_por_mascara(m))

    seen = set()
    out = []
    for n in names:
        if n not in seen:
            seen.add(n)
            out.append(n)
    return out


def habilitar_simbolo(symbol: str) -> bool:
    """Habilita o símbolo no Market Watch."""
    return bool(mt5.symbol_select(symbol, True))


def escolher_simbolo():
    """Escolhe o primeiro símbolo válido da lista de candidatos."""
    # Tenta os candidatos da lista
    for s in SYMBOL_CANDIDATOS:
        if mt5.symbol_info(s) is None:
            continue
        if not habilitar_simbolo(s):
            continue
        return s

    return None



def get_sp_tz():
    try:
        return ZoneInfo("America/Sao_Paulo")
    except ZoneInfoNotFoundError:
        # Opção A (recomendada): falhar e instruir instalar tzdata
        raise RuntimeError(
            "Timezone 'America/Sao_Paulo' não encontrado. "
            "Instale 'tzdata' (pip install tzdata) ou configure PYTHONTZPATH."
        )

        # Opção B (se você realmente quiser fallback):
        # return timezone(timedelta(hours=-3))



# Timezone de São Paulo (pode ser ZoneInfo, dateutil tz ou timezone fixo)
SP_TZ = get_sp_tz()


def sp_localize(d: datetime) -> datetime:
    """Interpreta um datetime naive como horário de São Paulo ou converte para SP."""
    if d.tzinfo is None:
        return d.replace(tzinfo=SP_TZ)
    return d.astimezone(SP_TZ)


def to_utc(d: datetime) -> datetime:
    """Converte um datetime (assumido em SP caso seja naive) para UTC."""
    if d.tzinfo is None:
        d = d.replace(tzinfo=SP_TZ)
    return d.astimezone(timezone.utc)


def utc_dt(d: datetime) -> datetime:
    """Compatibilidade: converte para UTC usando SP como default para datetimes naive."""
    return to_utc(d)


def convert_bar_to_dict(bar):
    """Converte uma barra OHLC do MT5 para um dicionário JSON serializable, incluindo timestamps ISO."""
    t_utc = datetime.fromtimestamp(int(bar['time']), timezone.utc)
    t_sp = t_utc.astimezone(SP_TZ)
    return {
        "time": int(bar['time']),
        "time_utc": t_utc.isoformat(),
        "time_sp": t_sp.isoformat(),
        "open": float(bar['open']),
        "high": float(bar['high']),
        "low": float(bar['low']),
        "close": float(bar['close']),
        "tick_volume": int(bar['tick_volume']),
        "spread": int(bar['spread']),
        "real_volume": int(bar['real_volume'])
    }


def get_ohlc_from_date(symbol: str, date: datetime, timeframe=mt5.TIMEFRAME_M1):
    # "Dia" em São Paulo
    start_sp = datetime(date.year, date.month, date.day, 9, 0, 0, tzinfo=SP_TZ)
    end_sp   = datetime(date.year, date.month, date.day, 9, 5, 0, tzinfo=SP_TZ)

    # Converter para UTC para chamar o MT5 (recomendado pela doc)
    start_utc = start_sp.astimezone(timezone.utc)
    end_utc   = end_sp.astimezone(timezone.utc)

    return mt5.copy_rates_range(symbol, timeframe, start_utc, end_utc)


def main():
    # Inicializa a conexão com o MetaTrader 5
    if not mt5.initialize():
        print(f"Falha ao inicializar MT5: {mt5.last_error()}")
        return
    
    print("MetaTrader 5 inicializado com sucesso!")
    print(f"Versão: {mt5.version()}")
    print("-" * 80)
    
    # Escolhe o símbolo válido da lista de candidatos
    symbol = escolher_simbolo()
    
    if symbol is None:
        print("[ERRO] Nenhum símbolo válido encontrado na lista de candidatos!")
        print(f"Candidatos testados: {SYMBOL_CANDIDATOS}")
        print(f"Símbolos WIN disponíveis: {listar_simbolos_win()}")
        mt5.shutdown()
        return
    
    print(f"Símbolo selecionado: {symbol}")
    print("-" * 80)
    
    # Data alvo: 17 de dezembro de 2025
    target_date = datetime(2025, 12, 16)
    print(f"Buscando barras OHLC para a data: {target_date.strftime('%d/%m/%Y')}")
    print(f"Timeframe: M1 (1 minuto)")
    print("-" * 80)
    
    print(f"\n{'='*80}")
    print(f"SÍMBOLO: {symbol}")
    print(f"{'='*80}")
    
    # Obtém as barras OHLC
    bars = get_ohlc_from_date(symbol, target_date, mt5.TIMEFRAME_M1)
    # Salva TODAS as barras com time/time_utc/time_sp
    bars_out = [convert_bar_to_dict(bar) for bar in bars]

    with open("ohlc_bars.json", "w", encoding="utf-8") as f:
        json.dump(
            {
                "symbol": symbol,
                "date": target_date.strftime("%Y-%m-%d"),
                "timeframe": "M1",
                "bars": bars_out,
            },
            f,
            indent=2,
            ensure_ascii=False,
        )

    
    
    if bars is None or len(bars) == 0:
        print(f"  [INFO] Nenhuma barra OHLC encontrada para '{symbol}' em {target_date.strftime('%d/%m/%Y')}")
    else:
        # Salva um exemplo de barra em JSON
        sample_bar = bars[0]
        with open("ohlc_sample.json", "w", encoding="utf-8") as f:
            json.dump({
                "symbol": symbol,
                "date": target_date.strftime('%Y-%m-%d'),
                "timeframe": "M1",
                "bar": convert_bar_to_dict(sample_bar)
            }, f, indent=2, ensure_ascii=False)
        
        print(f"  Exemplo de barra salvo em 'ohlc_sample.json'")
        
        # Printa todas as barras OHLC
        print(f"\n  BARRAS OHLC ({symbol}):")
        print(f"  {'-'*90}")
        print(f"  {'#':>5} | {'Time':^19} | {'Open':>10} | {'High':>10} | {'Low':>10} | {'Close':>10} | {'Volume':>8}")
        print(f"  {'-'*90}")
        
        # Abre o arquivo para salvar os resultados
        with open("results.txt", "w", encoding="utf-8") as f:
            f.write(f"BARRAS OHLC - {symbol} - {target_date.strftime('%d/%m/%Y')} - Timeframe: M1\n")
            f.write(f"{'='*100}\n\n")
            f.write(f"{'#':>5} | {'Time':^19} | {'Open':>10} | {'High':>10} | {'Low':>10} | {'Close':>10} | {'Volume':>8}\n")
            f.write(f"{'-'*100}\n")
            
            for i, bar in enumerate(bars):
                t_utc = datetime.fromtimestamp(int(bar['time']), timezone.utc)
                t_sp = t_utc.astimezone(SP_TZ)
                line = (f"{i+1:>5} | {t_sp.strftime('%Y-%m-%d %H:%M:%S'):^19} | "
                        f"{bar['open']:>10.2f} | {bar['high']:>10.2f} | "
                        f"{bar['low']:>10.2f} | {bar['close']:>10.2f} | "
                        f"{bar['tick_volume']:>8}")
                print(f"  {line}  (UTC {t_utc.strftime('%H:%M:%S')})")
                f.write(f"{line}\n")
            
            # Escreve a quantidade de barras
            f.write(f"\n{'='*100}\n")
            f.write(f"QUANTIDADE DE BARRAS: len(bars) = {len(bars)}\n")
        
        # Printa a quantidade de barras
        print(f"\n  {'-'*90}")
        print(f"  QUANTIDADE DE BARRAS: len(bars) = {len(bars)}")
        print(f"  {'-'*90}")
        print(f"\n  Resultados salvos em 'results.txt'")
        print(f"  Exemplo de barra salvo em 'ohlc_sample.json'")
    
    # Finaliza a conexão
    mt5.shutdown()
    print("\n" + "="*80)
    print("MetaTrader 5 finalizado.")


if __name__ == "__main__":
    main()
