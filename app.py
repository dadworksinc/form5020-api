from flask import Flask, request, send_file, jsonify
from flask_cors import CORS
from pypdf import PdfReader, PdfWriter
import requests
import io
import os
from datetime import datetime

app = Flask(__name__)
CORS(app)

PDF_URL = 'https://raw.githubusercontent.com/dadworksinc/risk-assets/main/form5020.pdf'

def fmt_date(val):
    """Convert any date format to mm/dd/yy for Form 5020."""
    if not val:
        return ''
    for fmt in ['%Y-%m-%d', '%m/%d/%Y', '%m/%d/%y', '%Y/%m/%d']:
        try:
            d = datetime.strptime(str(val)[:10], fmt)
            return d.strftime('%m/%d/%y')
        except:
            continue
    return str(val)[:10]

def fmt_time(val):
    """Convert HH:MM to 12-hour AM/PM format."""
    if not val:
        return ''
    try:
        parts = str(val).split(':')
        h = int(parts[0])
        m = parts[1] if len(parts) > 1 else '00'
        ampm = 'AM' if h < 12 else 'PM'
        h12 = h % 12 or 12
        return f'{h12}:{m} {ampm}'
    except:
        return str(val)

@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'ok'})

@app.route('/fill-form5020', methods=['POST', 'OPTIONS'])
def fill_form5020():
    if request.method == 'OPTIONS':
        return '', 204

    try:
        data = request.get_json()

        # Fetch the official PDF
        pdf_response = requests.get(PDF_URL, timeout=10)
        pdf_response.raise_for_status()

        reader = PdfReader(io.BytesIO(pdf_response.content))
        writer = PdfWriter()
        writer.append(reader)

        # Format dates and times
        injury_date   = fmt_date(data.get('injury_date', ''))
        injury_time   = fmt_time(data.get('injury_time', ''))
        shift_time    = fmt_time(data.get('shift_start_time', ''))
        knowledge_date = fmt_date(data.get('knowledge_date', ''))
        dwc1_date     = fmt_date(data.get('dwc1_date', ''))
        hire_date     = fmt_date(data.get('hire_date', ''))

        # Build field map
        fields = {
            '1_FIRM_NAME':                   data.get('firm_name', ''),
            'Ia_Policy_Number':              data.get('policy_number', ''),
            '2_MAILING_ADDRESS_Number':      data.get('mailing_address', ''),
            '2a_Phone_Number':               data.get('phone_number', ''),
            '4_NATURE_OF_BUSINESS_eg_P':     data.get('industry', ''),
            '7_DATE_OF_INJURY__ONSET_O':     injury_date,
            '8_AM2':                         injury_time,
            'AM1':                           shift_time,
            '17_DATE_OF_EMPLOYERS_KNOW':     knowledge_date,
            '18_DATE_EMPLOYEE_PROVIDED':     dwc1_date,
            '19_SPECIFIC_INJURYILLNESS':     data.get('injury_description', ''),
            '20_LOCATION_WHERE_EVENT_O':     data.get('location', ''),
            '20a_COUNTY':                    data.get('county', 'Riverside'),
            '22_DEPARTMENT_WHERE_EVENT':     data.get('department', ''),
            '24_EQUIPMENT_MATERIALS_AN':     data.get('equipment', ''),
            '25_SPECIFIC_ACTIVITY_THE':      data.get('activity', ''),
            '26_HOW_INJURY_ILLNESS':         data.get('description', ''),
            '27_name _address_of_physician': data.get('physician', ''),
            '29_HOSP_TA_ZED_AS_AN_NAl':     data.get('hospital_name', ''),
            '30_EMPLO_CC_NAME':              data.get('employee_name', ''),
            '33_HOME_ADDRESS_IN_be_Sto':     data.get('employee_address', ''),
            '33a_PHONE_NUMBER':              data.get('employee_phone', ''),
            '35_OCC_UPAT_ON_Ppqj_a_on':     data.get('occupation', ''),
            '36_DATE_OF_H_RE_mmiddlyy':      hire_date,
            'Completed_By_type_or_prin':     data.get('completed_by', ''),
        }

        # Radio/checkbox fields
        radio_fields = {
            'Group2':   '/Private',
            'Group6':   '/Yes',
            'Group3':   '/Yes' if data.get('lost_time') else '/No',
            'Group7':   '/Yes' if data.get('other_injured') else '/No',
            'Group8':   '/Yes' if data.get('hospitalized') else '/No',
            'Group9':   '/Yes' if data.get('er_treated') else '/No',
            'Group11':  '/Male' if data.get('is_male', True) else '/Female',
            'Group100': '/regular, full-time',
            'Group101': '/No',
        }

        # Write text fields
        writer.update_page_form_field_values(
            writer.pages[0],
            fields,
            auto_regenerate=False
        )

        # Write radio fields
        for field_name, value in radio_fields.items():
            try:
                writer.update_page_form_field_values(
                    writer.pages[0],
                    {field_name: value},
                    auto_regenerate=False
                )
            except Exception:
                pass

        # Save to buffer
        output = io.BytesIO()
        writer.write(output)
        output.seek(0)

        emp_name = data.get('employee_name', 'Unknown').replace(' ', '_')
        filename = f"Form5020_{emp_name}_{injury_date.replace('/', '-')}.pdf"

        return send_file(
            output,
            mimetype='application/pdf',
            as_attachment=True,
            download_name=filename
        )

    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)
