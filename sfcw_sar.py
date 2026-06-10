#!/usr/bin/env python3
"""
sfcw_sar.py — Stepped-Frequency CW SAR Data Collection
"""

import uhd
import numpy as np
import time, os, json, sys

# PARAMETERS

F_START      = 1.0e9
F_STOP       = 6.0e9
N_FREQ       = 501
SAMP_RATE    = 5.0e6
TX_GAIN      = 70
RX_GAIN      = 55
N_SETTLE     = 5_000
N_MEAS       = 10_000
N_POS        = 64
DX           = 0.015
TARGET_R     = 2.5
OUT_DIR      = os.path.expanduser("~/sar_data_sfcw")

# Derived

FREQS        = np.linspace(F_START, F_STOP, N_FREQ)
DF           = float(FREQS[1] - FREQS[0])
BW_TOTAL     = float(F_STOP - F_START)
RANGE_RES    = 3e8 / (2 * BW_TOTAL)
R_MAX        = 3e8 / (2 * DF)
WAVELENGTH   = 3e8 / ((F_START + F_STOP) / 2)
APERTURE_LEN = (N_POS - 1) * DX
CR_RES       = (3e8 / F_STOP) * TARGET_R / APERTURE_LEN

# CONSOLE HELPERS

RESET = "\033[0m"; GREEN = "\033[92m"; YELLOW = "\033[93m"
RED   = "\033[91m"; CYAN  = "\033[96m"; BOLD  = "\033[1m"

def log(msg, c=RESET):
    print(f"{c}[{time.strftime('%H:%M:%S')}] {msg}{RESET}")

def banner():
    print(f"\n{BOLD}{CYAN}{'='*60}")
    print(f"  SFCW SAR  —  USRP B210 + TBMA4")
    print(f"  Sweep    : {F_START/1e9:.0f} – {F_STOP/1e9:.0f} GHz  ({N_FREQ} steps × {DF/1e6:.0f} MHz)")
    print(f"  Total BW : {BW_TOTAL/1e9:.0f} GHz")
    print(f"  Range res: {RANGE_RES*100:.0f} cm   R_max = {R_MAX:.0f} m")
    print(f"  CR res   : {CR_RES*100:.0f} cm  (at {TARGET_R} m, {N_POS}×{DX*1000:.0f}mm aperture)")
    print(f"  SR       : {SAMP_RATE/1e6:.0f} MSPS  (stable — no underflows)")
    print(f"  Time/pos : ~{N_FREQ*(N_SETTLE+N_MEAS)/SAMP_RATE:.0f}s  Total ~{N_FREQ*(N_SETTLE+N_MEAS)/SAMP_RATE*N_POS/60:.0f} min")
    print(f"  Output   : {OUT_DIR}/")
    print(f"{'='*60}{RESET}\n")

# SINGLE FREQUENCY MEASUREMENT

def measure_frequency(usrp, rx_streamer, tx_streamer, freq):

    n_total  = N_SETTLE + N_MEAS
    rx_buf   = np.zeros(n_total, dtype=np.complex64)

    tune_req = uhd.libpyuhd.types.tune_request(freq)
    usrp.set_tx_freq(tune_req, 0)
    usrp.set_rx_freq(tune_req, 0)

    time.sleep(0.004)

    tx_buf = np.full(n_total + 200, 0.7 + 0j, dtype=np.complex64)
    tx_md  = uhd.types.TXMetadata()
    tx_md.start_of_burst = True
    tx_md.end_of_burst   = True
    tx_streamer.send(tx_buf, tx_md)

    stream_cmd = uhd.types.StreamCMD(uhd.types.StreamMode.num_done)
    stream_cmd.num_samps  = n_total
    stream_cmd.stream_now = True
    rx_streamer.issue_stream_cmd(stream_cmd)

    n_received = 0
    rx_md      = uhd.types.RXMetadata()
    deadline   = time.time() + 2.0

    while n_received < n_total:
        if time.time() > deadline:
            log(f"  RX timeout at {freq/1e9:.3f} GHz (got {n_received}/{n_total})", YELLOW)
            break
        chunk = rx_buf[n_received:]
        n     = rx_streamer.recv(chunk, rx_md, timeout=0.5)
        n_received += n

        if rx_md.error_code == uhd.types.RXMetadataErrorCode.overflow:
            log("  Overflow — reduce RX gain", YELLOW)
        elif rx_md.error_code not in (
                uhd.types.RXMetadataErrorCode.none,
                uhd.types.RXMetadataErrorCode.timeout):
            log(f"  RX error: {rx_md.strerror()}", YELLOW)
            break

    valid = rx_buf[N_SETTLE:n_received]
    if len(valid) == 0:
        return 0.0 + 0j
    return complex(np.mean(valid))

# MAIN

def main():
    banner()
    os.makedirs(OUT_DIR, exist_ok=True)

    log("Initialising USRP B210...", CYAN)
    try:
        usrp = uhd.usrp.MultiUSRP("")
    except Exception as e:
        log(f"USRP init failed: {e}", RED)
        sys.exit(1)

    usrp.set_rx_rate(SAMP_RATE, 0)
    usrp.set_tx_rate(SAMP_RATE, 0)
    usrp.set_rx_gain(RX_GAIN, 0)
    usrp.set_tx_gain(TX_GAIN, 0)
    usrp.set_rx_antenna("RX2", 0)
    usrp.set_tx_antenna("TX/RX", 0)

    st_args          = uhd.usrp.StreamArgs("fc32", "sc16")
    st_args.channels = [0]
    rx_streamer      = usrp.get_rx_stream(st_args)
    tx_streamer      = usrp.get_tx_stream(st_args)

    log("Hardware check at 3.5 GHz...", CYAN)
    test_val = measure_frequency(usrp, rx_streamer, tx_streamer, 3.5e9)
    log(f"  Test amplitude: {abs(test_val):.5f}", GREEN)

    input("Press Enter to start...")

    S = np.zeros((N_POS, N_FREQ), dtype=np.complex128)

    for pos in range(N_POS):

        print(f"\nMove antenna to position {pos+1}/{N_POS} (x = {pos*DX*100:.1f} cm)")
        input("Press Enter when ready...")

        row = np.zeros(N_FREQ, dtype=np.complex128)

        for fi, freq in enumerate(FREQS):
            print(f"\rFreq {fi+1}/{N_FREQ}", end="", flush=True)
            row[fi] = measure_frequency(usrp, rx_streamer, tx_streamer, freq)

        print()  # clean line after sweep

        S[pos, :] = row

        # ✅ SAVE EACH POSITION
        pos_path = os.path.join(OUT_DIR, f"pos_{pos:04d}.npy")
        np.save(pos_path, row)

    matrix_path = os.path.join(OUT_DIR, "sfcw_matrix.npy")
    np.save(matrix_path, S.astype(np.complex64))
    log(f"Matrix saved: {matrix_path}", GREEN)

    try:
        import scipy.io as sio
        mat_path = os.path.join(OUT_DIR, "sfcw_matrix.mat")
        sio.savemat(mat_path, {"S": S.astype(np.complex64)})
        log(f"MAT file: {mat_path}", GREEN)
    except ImportError:
        log("scipy not found", YELLOW)

if __name__ == "__main__":
    main()
