import streamlit as st
import pandas as pd
import numpy as np
from datetime import date
from download import download_button

st.set_page_config(layout='wide')

# payroll_df = 'files/Custom_Payroll_Report.xlsx'
# schedule_df = 'files/Shifts Schedule.csv'
# deducted_df = 'files/Hours Scheduled.csv'

def labour_costs(payroll_df,schedule_df,deducted_df):
    # Initialized Custom Payroll dataframe
    df1 = pd.read_excel(payroll_df)
    df1 = df1[['Code','Employee', 'Branch','Department','Unit','Total Earning']]

    # delete last row
    df1.drop(df1.tail(1).index,inplace=True)

    # type conversion
    df1['Code'] = df1['Code'].astype('int')
    df1['Unit'].replace(np.nan,0, inplace=True)
    df1['Unit'] = df1['Unit'].astype('int64')

    # Initialized Shifts dataframe
    df2 = pd.read_csv(schedule_df)
    del df2['Salary']
    del df2['start_day']
    del df2['end_day']
    del df2['start_time']
    del df2['end_time']

    # Initialized Shifts lookup dataframe
    df2_lookup = df2[['id','total_time']]
    df2_lookup['id'] = df2_lookup['id'].astype('object')
    df2_lookup['total_time'] = df2_lookup['total_time'].astype('float')
    df2_lookup = df2_lookup.groupby(['id'], as_index=False)['total_time'].sum() # grouping rows
    df2_lookup = df2_lookup.rename(columns={"total_time":"total_shift_time"})

    # pysqldf = lambda q: sqldf(q, globals())

    # q = """
    #     SELECT id, sum(total_time) as total_time
    #     FROM df2_lookup
    #     GROUP BY id, total_time
    #     ORDER BY id 
    # """
    # df2_lookup = pysqldf(q)

    # routine cleanup of the Shifts dataframe
    df2 = df2.rename(columns={"employee":"employee_name"})
    df2['location'].replace('Umoja Clinic','Umoja 2',inplace=True)
    df2['remote_site'] = df2['remote_site'].astype('object')
    df2['remote_site'].replace(np.nan,'Blank',inplace=True)
    df2['eid'].replace(np.nan,0, inplace=True)
    df2['eid'] = df2['eid'].astype('int64')

    # check for remote site to amalgamate locations for mc movements
    # df2['location'] = np.where(
    #     df2['location'] == df2['remote_site'] or df2['remote_site'] == "Blank",
    #     df2['location'],
    #     df2['remote_site']
    # )

    # merge with Payroll dataframe
    df2 = pd.merge(
        df2,
        df1,
        left_on='eid',
        right_on = 'Code',
        how = 'left'
    )

    # Grouping the dataframe rows
    df2 = df2.groupby(['employee_name', 'id', 'eid', 'location', 'Code','Employee','Department','Unit','Total Earning'], as_index=False)['total_time'].sum()

    # Routine cleanup of the dataframe
    df2['Unit'] = df2['Unit'].astype('int')
    del df2['Code']
    del df2['employee_name']

    # merge with Shift lookup to get total shift time
    df2 = pd.merge(
        df2,
        df2_lookup,
        on='id',
        how = 'left'
    )

    # Initialized Hours Scheduled with breaks deducted
    # df3 = pd.read_csv('files/Hours Scheduled.csv')
    df3 = pd.read_csv(deducted_df)

    # Routine clean up of dataframe
    df3['Id'] = df3['Id'].astype('int64')
    df3 = df3.rename(columns={"Hours":"Deducted_Breaks"})

    # merge with deducted breaks dataframe
    df2 = pd.merge(
        df2,
        df3,
        left_on = 'id',
        right_on = 'Id',
        how = 'left'
    )

    # routine clean up of dataframe
    del df2['Id']
    del df2['Eid']
    del df2['Name']

    # Calculation of Labour Cost
    df2['total_break_time'] = df2['total_time'] - df2['Deducted_Breaks']
    df2['break_ratio'] = df2['total_break_time']/df2['total_shift_time']
    df2['total_time_less_breaks'] = df2['total_shift_time'] - (df2['total_shift_time'] * df2['break_ratio'])
    # df2['Labour_Cost'] = (df2['total_time_less_breaks']/df2['Deducted_Breaks']) * df2['Total Earning']
    df2['Labour_Cost'] = (df2['total_time']/df2['total_shift_time']) * df2['Total Earning']

    # identify unallocated staff
    df1 = df1.assign(mc_staff = df1.Code.isin(df2.eid))

    # filter out mc staff
    df1 = df1[ df1['mc_staff'] == False ]
    del df1['mc_staff']

    # create 1st union dataframe
    column_names = [
        "*ContactName",
        "EmailAddress",
        "POAddressLine1",
        "POAddressLine2",
        "POAddressLine3",
        "POAddressLine4",
        "POCity",
        "PORegion",
        "POPostalCode",
        "POCountry",
        "*InvoiceNumber",
        "*InvoiceDate",
        "*DueDate",
        "Total",
        "InventoryItemCode",
        "Description",
        "*Quantity",
        "*UnitAmount",
        "*AccountCode",
        "*TaxType",
        "TaxAmount",
        "TrackingName1",
        "TrackingOption1",
        "TrackingName2",
        "TrackingOption2",
        "Currency",
    ]

    df_union_1 = pd.DataFrame(columns=column_names, index=None)

    # assign data to columns
    df_union_1["*ContactName"] = df1['Code']
    df_union_1["*InvoiceNumber"] = df1['Code']
    df_union_1["*ContactName"] = df1['Code']
    df_union_1["*InvoiceDate"] = date.today()
    df_union_1["*DueDate"] = date.today()
    df_union_1["Description"] = df1["Employee"]
    df_union_1["*Quantity"] = 1
    df_union_1["*UnitAmount"] = df1['Total Earning']
    df_union_1["*AccountCode"] = df1['Unit']
    df_union_1["*TaxType"] = "Tax Exempt"
    df_union_1["TrackingName1"] = "Location"
    df_union_1["TrackingOption1"] = df1["Branch"]
    df_union_1["TrackingName2"] = "Department"

    print(df_union_1)

    # create 2nd union dataframe
    df_union_2 = pd.DataFrame(columns=column_names, index=None)

    # assign data to columns
    df_union_2["*ContactName"] = df2['eid']
    df_union_2["*InvoiceNumber"] = df2['eid']
    df_union_2["*ContactName"] = df2['eid']
    df_union_2["*InvoiceDate"] = date.today()
    df_union_2["*DueDate"] = date.today()
    df_union_2["Description"] = df2["Employee"]
    df_union_2["*Quantity"] = 1
    df_union_2["*UnitAmount"] = df2['Labour_Cost']
    df_union_2["*AccountCode"] = df2['Unit']
    df_union_2["*TaxType"] = "Tax Exempt"
    df_union_2["TrackingName1"] = "Location"
    df_union_2["TrackingOption1"] = df2["location"]
    df_union_2["TrackingName2"] = "Department"

    df_union_2 = df_union_2.append(df_union_1, ignore_index = True)

    df_union_2['GS'] = "GS"

    df_union_2["*ContactName"] = df_union_2['GS'] + " " + df_union_2["*ContactName"].astype('str')
    df_union_2["*InvoiceNumber"] = df_union_2['GS'] + " " + df_union_2["*InvoiceNumber"].astype('str')
    df_union_2["*UnitAmount"] = df_union_2["*UnitAmount"].round(decimals = 2)
    df_union_2.replace('Call Center','Support Office',inplace=True)

    del df_union_2['GS']

    st.header(f"Xero Gross Upload as at {date.today()}")
    st.dataframe(df_union_2)

    sum_of_salaries = df_union_2['*UnitAmount'].sum(axis = 0, skipna = True)

    st.write(f"The sum of total earnings after splitting costs to the respective cost centers is {sum_of_salaries}")

    download_button_str = download_button(df_union_2, f"Gross Upload as at {date.today()}.csv", 'Download CSV', pickle_it=False)
    st.markdown(download_button_str, unsafe_allow_html=True)

payroll_df = st.sidebar.file_uploader('Upload Custom Payroll Data in .xlsx format')
schedule_df = st.sidebar.file_uploader('Upload Shifts Schedule Data in .csv format')
deducted_df = st.sidebar.file_uploader('Upload Hours Scheduled with Deducted Breaks Data in .csv format')

if payroll_df == None or schedule_df == None or deducted_df == None:
    st.warning("Please upload all required files!")
    print(type(payroll_df))
else:
    st.info("Files uploaded successfully")
    print(type(payroll_df))
    labour_costs(payroll_df,schedule_df,deducted_df)