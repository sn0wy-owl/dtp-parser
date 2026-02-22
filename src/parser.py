import pandas as pd
from typing import Union

def parse_data(data: dict) -> Union[pd.DataFrame, None]:
    try:
        dtp_cards = data['results']['region_list'][0]['pok_list'][0]['result'][0]['dtpcardlist']['info_dtp']
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
                participant_info['car_mark'] = participant['marka_ts']
                participant_info['car_model'] = participant['m_ts']
                participant_info['color'] = participant['color']
                participant_info['car_year'] = participant['g_v']

                # информация о водителе
                for passenger in participant.get('ts_uch', []):
                    if passenger['kt_uch'] == 'Водитель':
                        participant_info['driver_gender'] = passenger['pol']
                        participant_info['driver_exp'] = passenger['v_st']
                        participant_info['driver_safety_belt'] = passenger['safety_belt']
                        participant_info['driver_alco'] = passenger['alco']
                        participant_info['driver_trauma'] = passenger['s_t']
                        participant_info['driver_violations'] = passenger['npdd']
                    
                        parsed_info.append(participant_info)

        except Exception as e:
            error_parse += 1

    return pd.DataFrame(parsed_info)
