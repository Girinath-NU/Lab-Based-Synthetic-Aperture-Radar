#!/usr/bin/env python3
# -*- coding: utf-8 -*-

#
# SPDX-License-Identifier: GPL-3.0
#
# GNU Radio Python Flow Graph
# Title: Robust FMCW SAR 6 GHz
# Author: SAR Lab
# Description: Robust FMCW SAR capture - USRP B210 + TBMA4 @ 6 GHz. Includes 300ms pre-trigger settling, exact sample capture, beat spectrum and time-domain monitors. Run via run_sar.py.

# GNU Radio version: 3.10.1.1

from gnuradio import analog
from gnuradio import blocks
from gnuradio import filter
from gnuradio.filter import firdes
from gnuradio import gr
from gnuradio.fft import window
import sys
import signal
from argparse import ArgumentParser
from gnuradio.eng_arg import eng_float, intx
from gnuradio import eng_notation
from gnuradio import uhd
import time




class fmcw_sar_robust(gr.top_block):

    def __init__(self, out_file='/tmp/sar_pos_0000.bin'):
        gr.top_block.__init__(self, "Robust FMCW SAR 6 GHz", catch_exceptions=True)

        ##################################################
        # Parameters
        ##################################################
        self.out_file = out_file

        ##################################################
        # Variables
        ##################################################
        self.sweep_time = sweep_time = 0.001
        self.samp_rate = samp_rate = 5e6
        self.n_samp_chirp = n_samp_chirp = int(samp_rate * sweep_time)
        self.n_chirps = n_chirps = 32
        self.tx_gain = tx_gain = 70
        self.rx_gain = rx_gain = 50
        self.n_settle = n_settle = int(0.3 * samp_rate)
        self.n_capture = n_capture = n_chirps * n_samp_chirp
        self.lpf_trans = lpf_trans = 400
        self.lpf_cutoff = lpf_cutoff = 2000
        self.chirp_bw = chirp_bw = 5e6
        self.center_freq = center_freq = 6000000000

        ##################################################
        # Blocks
        ##################################################
        self.uhd_usrp_source_0 = uhd.usrp_source(
            ",".join(("", "", "master_clock_rate=40e6")),
            uhd.stream_args(
                cpu_format="fc32",
                args='',
                channels=list(range(0,1)),
            ),
        )
        self.uhd_usrp_source_0.set_subdev_spec('A:A', 0)
        self.uhd_usrp_source_0.set_samp_rate(samp_rate)
        # No synchronization enforced.

        self.uhd_usrp_source_0.set_center_freq(center_freq, 0)
        self.uhd_usrp_source_0.set_antenna("RX2", 0)
        self.uhd_usrp_source_0.set_gain(rx_gain, 0)
        self.uhd_usrp_sink_0 = uhd.usrp_sink(
            ",".join(("", "", "master_clock_rate=40e6")),
            uhd.stream_args(
                cpu_format="fc32",
                args='',
                channels=list(range(0,1)),
            ),
            '',
        )
        self.uhd_usrp_sink_0.set_subdev_spec('A:A', 0)
        self.uhd_usrp_sink_0.set_samp_rate(samp_rate)
        # No synchronization enforced.

        self.uhd_usrp_sink_0.set_center_freq(center_freq, 0)
        self.uhd_usrp_sink_0.set_antenna("TX/RX", 0)
        self.uhd_usrp_sink_0.set_gain(tx_gain, 0)
        self.low_pass_filter_0 = filter.fir_filter_ccf(
            1,
            firdes.low_pass(
                1,
                samp_rate,
                lpf_cutoff,
                lpf_trans,
                window.WIN_HAMMING,
                6.76))
        self.blocks_skiphead_0 = blocks.skiphead(gr.sizeof_gr_complex*1, n_settle)
        self.blocks_multiply_const_vxx_0 = blocks.multiply_const_cc(0.7)
        self.blocks_multiply_conjugate_cc_0 = blocks.multiply_conjugate_cc(1)
        self.blocks_head_0 = blocks.head(gr.sizeof_gr_complex*1, n_capture)
        self.blocks_file_sink_0 = blocks.file_sink(gr.sizeof_gr_complex*1, out_file, False)
        self.blocks_file_sink_0.set_unbuffered(True)
        self.analog_sig_source_x_0 = analog.sig_source_f(samp_rate, analog.GR_SAW_WAVE, 1.0/sweep_time, chirp_bw, (-chirp_bw/2), 0)
        self.analog_frequency_modulator_fc_0 = analog.frequency_modulator_fc(2*3.14159265358979/samp_rate)


        ##################################################
        # Connections
        ##################################################
        self.connect((self.analog_frequency_modulator_fc_0, 0), (self.blocks_multiply_const_vxx_0, 0))
        self.connect((self.analog_sig_source_x_0, 0), (self.analog_frequency_modulator_fc_0, 0))
        self.connect((self.blocks_head_0, 0), (self.blocks_file_sink_0, 0))
        self.connect((self.blocks_multiply_conjugate_cc_0, 0), (self.low_pass_filter_0, 0))
        self.connect((self.blocks_multiply_const_vxx_0, 0), (self.blocks_multiply_conjugate_cc_0, 1))
        self.connect((self.blocks_multiply_const_vxx_0, 0), (self.uhd_usrp_sink_0, 0))
        self.connect((self.blocks_skiphead_0, 0), (self.blocks_head_0, 0))
        self.connect((self.low_pass_filter_0, 0), (self.blocks_skiphead_0, 0))
        self.connect((self.uhd_usrp_source_0, 0), (self.blocks_multiply_conjugate_cc_0, 0))


    def get_out_file(self):
        return self.out_file

    def set_out_file(self, out_file):
        self.out_file = out_file
        self.blocks_file_sink_0.open(self.out_file)

    def get_sweep_time(self):
        return self.sweep_time

    def set_sweep_time(self, sweep_time):
        self.sweep_time = sweep_time
        self.set_n_samp_chirp(int(self.samp_rate * self.sweep_time))
        self.analog_sig_source_x_0.set_frequency(1.0/self.sweep_time)

    def get_samp_rate(self):
        return self.samp_rate

    def set_samp_rate(self, samp_rate):
        self.samp_rate = samp_rate
        self.set_n_samp_chirp(int(self.samp_rate * self.sweep_time))
        self.set_n_settle(int(0.3 * self.samp_rate))
        self.analog_frequency_modulator_fc_0.set_sensitivity(2*3.14159265358979/self.samp_rate)
        self.analog_sig_source_x_0.set_sampling_freq(self.samp_rate)
        self.low_pass_filter_0.set_taps(firdes.low_pass(1, self.samp_rate, self.lpf_cutoff, self.lpf_trans, window.WIN_HAMMING, 6.76))
        self.uhd_usrp_sink_0.set_samp_rate(self.samp_rate)
        self.uhd_usrp_source_0.set_samp_rate(self.samp_rate)

    def get_n_samp_chirp(self):
        return self.n_samp_chirp

    def set_n_samp_chirp(self, n_samp_chirp):
        self.n_samp_chirp = n_samp_chirp
        self.set_n_capture(self.n_chirps * self.n_samp_chirp)

    def get_n_chirps(self):
        return self.n_chirps

    def set_n_chirps(self, n_chirps):
        self.n_chirps = n_chirps
        self.set_n_capture(self.n_chirps * self.n_samp_chirp)

    def get_tx_gain(self):
        return self.tx_gain

    def set_tx_gain(self, tx_gain):
        self.tx_gain = tx_gain
        self.uhd_usrp_sink_0.set_gain(self.tx_gain, 0)

    def get_rx_gain(self):
        return self.rx_gain

    def set_rx_gain(self, rx_gain):
        self.rx_gain = rx_gain
        self.uhd_usrp_source_0.set_gain(self.rx_gain, 0)

    def get_n_settle(self):
        return self.n_settle

    def set_n_settle(self, n_settle):
        self.n_settle = n_settle

    def get_n_capture(self):
        return self.n_capture

    def set_n_capture(self, n_capture):
        self.n_capture = n_capture
        self.blocks_head_0.set_length(self.n_capture)

    def get_lpf_trans(self):
        return self.lpf_trans

    def set_lpf_trans(self, lpf_trans):
        self.lpf_trans = lpf_trans
        self.low_pass_filter_0.set_taps(firdes.low_pass(1, self.samp_rate, self.lpf_cutoff, self.lpf_trans, window.WIN_HAMMING, 6.76))

    def get_lpf_cutoff(self):
        return self.lpf_cutoff

    def set_lpf_cutoff(self, lpf_cutoff):
        self.lpf_cutoff = lpf_cutoff
        self.low_pass_filter_0.set_taps(firdes.low_pass(1, self.samp_rate, self.lpf_cutoff, self.lpf_trans, window.WIN_HAMMING, 6.76))

    def get_chirp_bw(self):
        return self.chirp_bw

    def set_chirp_bw(self, chirp_bw):
        self.chirp_bw = chirp_bw
        self.analog_sig_source_x_0.set_amplitude(self.chirp_bw)
        self.analog_sig_source_x_0.set_offset((-self.chirp_bw/2))

    def get_center_freq(self):
        return self.center_freq

    def set_center_freq(self, center_freq):
        self.center_freq = center_freq
        self.uhd_usrp_sink_0.set_center_freq(self.center_freq, 0)
        self.uhd_usrp_source_0.set_center_freq(self.center_freq, 0)



def argument_parser():
    description = 'Robust FMCW SAR capture - USRP B210 + TBMA4 @ 6 GHz. Includes 300ms pre-trigger settling, exact sample capture, beat spectrum and time-domain monitors. Run via run_sar.py.\n'
    parser = ArgumentParser(description=description)
    parser.add_argument(
        "-o", "--out-file", dest="out_file", type=str, default='/tmp/sar_pos_0000.bin',
        help="Set Output file path [default=%(default)r]")
    return parser


def main(top_block_cls=fmcw_sar_robust, options=None):
    if options is None:
        options = argument_parser().parse_args()
    tb = top_block_cls(out_file=options.out_file)

    def sig_handler(sig=None, frame=None):
        tb.stop()
        tb.wait()

        sys.exit(0)

    signal.signal(signal.SIGINT, sig_handler)
    signal.signal(signal.SIGTERM, sig_handler)

    tb.start()

    tb.wait()


if __name__ == '__main__':
    main()
