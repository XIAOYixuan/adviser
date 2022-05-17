###############################################################################
#
# Copyright 2020, University of Stuttgart: Institute for Natural Language Processing (IMS)
#
# This file is part of Adviser.
# Adviser is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3.
#
# Adviser is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Adviser.  If not, see <https://www.gnu.org/licenses/>.
#
###############################################################################

"""
This module allows to chat with the dialog system.
"""

import argparse
import os

from services.bst import HandcraftedBST
from services.domain_tracker.domain_tracker import DomainTracker
from services.service import DialogSystem
from utils.logger import DiasysLogger, LogLevel


def load_console():
    from services.hci.console import ConsoleInput, ConsoleOutput
    user_in = ConsoleInput(domain="")
    user_out = ConsoleOutput(domain="")
    return [user_in, user_out]

def load_nlg(backchannel: bool, domain = None):
    if backchannel:
        from services.nlg import BackchannelHandcraftedNLG
        nlg = BackchannelHandcraftedNLG(domain=domain, sub_topic_domains={'predicted_BC': ''})
    else:
        from services.nlg.nlg import HandcraftedNLG
        nlg = HandcraftedNLG(domain=domain)
    return nlg

def load_lecturers_domain(backchannel: bool = False):
    from utils.domain.jsonlookupdomain import JSONLookupDomain
    from services.nlu.nlu import HandcraftedNLU
    from services.nlg.nlg import HandcraftedNLG
    from services.policy import HandcraftedPolicy
    domain = JSONLookupDomain('ImsLecturers', display_name="Lecturers")
    lect_nlu = HandcraftedNLU(domain=domain)
    lect_bst = HandcraftedBST(domain=domain)
    lect_policy = HandcraftedPolicy(domain=domain)
    lect_nlg = load_nlg(backchannel=backchannel, domain=domain)
    return domain, [lect_nlu, lect_bst, lect_policy, lect_nlg]

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='ADVISER 2.0 Dialog System')
    parser.add_argument('--debug', action='store_true', help="enable debug mode")
    parser.add_argument('--log_file', choices=['info', 'errors', 'none'], 
                        default="none",
                        help="specify file log level")
    parser.add_argument('--log', choices=['info', 'errors', 'none'], 
                        default="results",
                        help="specify console log level")
    parser.add_argument('--cuda', action='store_true', help="enable cuda (currently only for asr/tts)")
    parser.add_argument('--privacy', action='store_true',
                        help="enable random mutations of the recorded voice to mask speaker identity", default=False)
    
    args = parser.parse_args()

    domains = []
    services = []

    # setup logger
    file_log_lvl = LogLevel[args.log_file.upper()]
    log_lvl = LogLevel[args.log.upper()]
    conversation_log_dir = './conversation_logs'
    logger = DiasysLogger(file_log_lvl=file_log_lvl,
                          console_log_lvl=log_lvl,
                          logfile_folder=conversation_log_dir,
                          logfile_basename="full_log")

    # load domain specific services
    l_domain, l_services = load_lecturers_domain(backchannel=False)
    domains.append(l_domain)
    services.extend(l_services)
    services.extend(load_console())

    # setup dialog system
    services.append(DomainTracker(domains=domains))
    debug_logger = logger if args.debug else None
    ds = DialogSystem(services=services, debug_logger=debug_logger)
    error_free = ds.is_error_free_messaging_pipeline()
    if not error_free:
        ds.print_inconsistencies()
    if args.debug:
        ds.draw_system_graph()


    try:
        ds.run_dialog({'gen_user_utterance': ""})
        ds.shutdown()
    except:
        import traceback
        print("##### EXCEPTION #####")
        traceback.print_exc()