import MetaTrader5 as mt5
from datetime import datetime, timezone
import json

# Lista de símbolos candidatos
SYMBOL_CANDIDATOS = [
    "WIN$",
    "WINFUT",
    "WIN@",
    "WIN@N",
    "WINZ25",
    "WING26",
    "WINJ26",
    "WINM26",
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
    """Escolhe o primeiro símbolo válido da lista de candidatos ou busca por máscara."""
    # Primeiro tenta os candidatos da lista
    for s in SYMBOL_CANDIDATOS:
        if mt5.symbol_info(s) is None:
            continue
        if not habilitar_simbolo(s):
            continue
        return s

    # Se não encontrou, busca por máscara
    for s in listar_simbolos_win():
        if mt5.symbol_info(s) is None:
            continue
        if not habilitar_simbolo(s):
            continue
        return s

    return None


def convert_tick_to_dict(tick):
    """Converte um tick do MT5 para um dicionário JSON serializable."""
    return {
        "time": int(tick['time']),
        "bid": float(tick['bid']),
        "ask": float(tick['ask']),
        "last": float(tick['last']),
        "volume": int(tick['volume']),
        "time_msc": int(tick['time_msc']),
        "flags": int(tick['flags']),
        "volume_real": float(tick['volume_real'])
    }


def utc_dt(d: datetime) -> datetime:
    """Converte datetime para UTC para uso nas funções do MT5."""
    if d.tzinfo is None:
        return d.replace(tzinfo=timezone.utc)
    return d.astimezone(timezone.utc)


def get_ticks_from_date(symbol: str, date: datetime):
    """
    Obtém todos os ticks de um símbolo para uma data específica.
    """
    # Define o intervalo do dia inteiro
    date_from = utc_dt(datetime(date.year, date.month, date.day, 0, 0, 0))
    date_to = utc_dt(datetime(date.year, date.month, date.day, 23, 59, 59))
    
    # Obtém os ticks
    ticks = mt5.copy_ticks_range(symbol, date_from, date_to, mt5.COPY_TICKS_ALL)
    
    return ticks


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
    target_date = datetime(2025, 12, 17)
    print(f"Buscando ticks para a data: {target_date.strftime('%d/%m/%Y')}")
    print("-" * 80)
    
    print(f"\n{'='*80}")
    print(f"SÍMBOLO: {symbol}")
    print(f"{'='*80}")
    
    # Obtém os ticks
    ticks = get_ticks_from_date(symbol, target_date)
    
    if ticks is None or len(ticks) == 0:
        print(f"  [INFO] Nenhum tick encontrado para '{symbol}' em {target_date.strftime('%d/%m/%Y')}")
    else:
        # Salva um exemplo de tick em JSON
        sample_tick = ticks[0]
        with open("tick.json", "w", encoding="utf-8") as f:
            json.dump({
                "symbol": symbol,
                "date": target_date.strftime('%Y-%m-%d'),
                "tick": convert_tick_to_dict(sample_tick)
            }, f, indent=2, ensure_ascii=False)
        
        print(f"  Exemplo de tick salvo em 'tick.json'")
        
        # Printa todos os ticks
        print(f"\n  TICKS ({symbol}):")
        print(f"  {'-'*70}")
        
        # Abre o arquivo para salvar os resultados
        with open("results.txt", "w", encoding="utf-8") as f:
            f.write(f"TICKS - {symbol} - {target_date.strftime('%d/%m/%Y')}\n")
            f.write(f"{'='*80}\n\n")
            
            for i, tick in enumerate(ticks):
                tick_time = datetime.fromtimestamp(tick['time'])
                line = (f"[{i+1}] Time: {tick_time} | "
                        f"Bid: {tick['bid']:.2f} | "
                        f"Ask: {tick['ask']:.2f} | "
                        f"Last: {tick['last']:.2f} | "
                        f"Volume: {tick['volume']}")
                print(f"  {line}")
                f.write(f"{line}\n")
            
            
            # Escreve a quantidade de ticks
            f.write(f"\n{'='*80}\n")
            f.write(f"QUANTIDADE DE TICKS: len(ticks) = {len(ticks)}\n")
        
        # Printa a quantidade de ticks
        print(f"\n  {'-'*70}")
        print(f"  QUANTIDADE DE TICKS: len(ticks) = {len(ticks)}")
        print(f"  {'-'*70}")
        print(f"\n  Resultados salvos em 'results.txt'")
        print(f"  Exemplo de tick salvo em 'tick.json'")
    
    # Finaliza a conexão
    mt5.shutdown()
    print("\n" + "="*80)
    print("MetaTrader 5 finalizado.")


if __name__ == "__main__":
    main()
