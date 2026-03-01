import pandas as pd
from typing import Union

from src.utils import get_health_status

def parse_data(data: dict) -> Union[pd.DataFrame, None]:
    try:
        dtp_cards = (
            data.get('results', {})
                  .get('region_list', [{}])[0]
                  .get('pok_list', [{}])[0]
                  .get('result', [{}])[0]
                  .get('dtpcardlist', {})
                  .get('info_dtp', [])
        )
    except Exception as e:
        return None

    parsed_info = []
    error_parse = 0
    
    for dtp_card in dtp_cards:
        try:
            base_info = {
                'id': dtp_card.get('empt_number'),
                'date': dtp_card.get('date_dtp'),
                'time': dtp_card.get('time'),
                'lat': dtp_card.get('coord_w'),
                'lng': dtp_card.get('coord_l'),
                'dtp_type': dtp_card.get('dtpv'),
                'road_title': dtp_card.get('dor')
            }

            # информация о погоде
            weather_dict = dtp_card.get('dor_usl', {})

            base_info['weather'] = weather_dict.get('spog')
            base_info['road_cond'] = weather_dict.get('s_pch')
            
            # информация об участниках
            for participant in dtp_card.get('ts_info', []):
                participant_info = base_info.copy()
                participant_info['car_mark'] = participant.get('marka_ts', '')
                participant_info['car_model'] = participant.get('m_ts', '')
                participant_info['color'] = participant.get('color', '')
                participant_info['car_year'] = participant.get('g_v', '')

                death_count = 0
                wounded_count = 0
                passenger_count = 0

                # информация о водителе
                for passenger in participant.get('ts_uch', []):
                    if passenger.get('kt_uch', '') == 'Водитель':
                        participant_info['driver_gender'] = passenger.get('pol', '')
                        participant_info['driver_exp'] = passenger.get('v_st', '')
                        participant_info['driver_safety_belt'] = passenger.get('safety_belt', '')
                        participant_info['driver_alco'] = passenger.get('alco', '')
                        participant_info['driver_violations'] = passenger.get('npdd', '')

                        driver_trauma = passenger.get('s_t', '')
                        driver_trauma_clear = get_health_status(driver_trauma)

                        if driver_trauma_clear == 'Скончался':
                            death_count += 1
                        elif driver_trauma_clear == 'Раненый':
                            wounded_count += 1
                    else:
                        passenger_count += 1

                        passenger_trauma = passenger.get('s_t', '')
                        passenger_trauma_clear = get_health_status(passenger_trauma)

                        if passenger_trauma_clear == 'Скончался':
                            death_count += 1
                        elif passenger_trauma_clear == 'Раненый':
                            wounded_count += 1

                participant_info['passenger_count'] = passenger_count
                participant_info['death_count'] = death_count
                participant_info['wounded_count'] = wounded_count
                parsed_info.append(participant_info)

        except Exception as e:
            error_parse += 1

    return pd.DataFrame(parsed_info)
