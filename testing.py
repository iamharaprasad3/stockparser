import streamlit as st
import pandas as pd
import asyncio
import httpx
from bs4 import BeautifulSoup

async def scrape(symbol):
    url = f'https://www.screener.in/company/{symbol}/consolidated/'
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            ratios = soup.find_all('span', class_='name')
            data = {'ROCE': None, 'ROE': None, 'P/E': None, 'Dividend Yield': None}
            for ratio in ratios:
                if 'ROCE' in ratio.text:
                    roce_value = ratio.find_next('span', class_='number').text
                    data['ROCE'] = roce_value
                if 'ROE' in ratio.text:
                    roe_value = ratio.find_next('span', class_='number').text
                    data['ROE'] = roe_value
                if 'P/E' in ratio.text:
                    pe_value = ratio.find_next('span', class_='number').text
                    data['P/E'] = pe_value
                if 'Dividend Yield' in ratio.text:
                    dy_value = ratio.find_next('span', class_='number').text
                    data['Dividend Yield'] = dy_value
            return data

async def main():
    st.sidebar.header('Upload Excel File')
    uploaded_file = st.sidebar.file_uploader('Choose Excel file', type=['xlsx'])

    if uploaded_file is not None:
        df_uploaded = pd.read_excel(uploaded_file)
        symbol_column = st.sidebar.selectbox('Select Symbol Column', options=df_uploaded.columns)
        buying_price_column = st.sidebar.selectbox('Select Buying Price Column', options=df_uploaded.columns)
        quantity_column = st.sidebar.selectbox('Select Quantity Column', options=df_uploaded.columns)
        
        if st.sidebar.button('Start'):
            symbols = df_uploaded[symbol_column].tolist()
            buying_prices = df_uploaded[buying_price_column].tolist()
            quantities = df_uploaded[quantity_column].tolist()
            
            scraped_data = []
            spinner = st.spinner("In Progress...")
            with spinner:
                tasks = [scrape(symbol.strip()) for symbol in symbols]
                results = await asyncio.gather(*tasks)
                for data, buying_price, quantity in zip(results, buying_prices, quantities):
                    if data:
                        total_value = buying_price * quantity
                        data['Total Value'] = total_value
                        
                        if 'Dividend Yield' in data:
                            dividend_yield = float(data['Dividend Yield'].replace('%', '')) / 100
                            total_dividend = total_value * dividend_yield
                            dividend_per_share = buying_price * dividend_yield
                            data['Dividend Per Share'] = dividend_per_share
                            data['Total Dividend'] = total_dividend
                        else:
                            data['Total Dividend'] = None
                    scraped_data.append(data)
            
            scraped_df = pd.DataFrame(scraped_data)
            merged_df = pd.concat([df_uploaded, scraped_df], axis=1)
            
            total_dividend_sum = merged_df['Total Dividend'].sum()
            total_value_sum = merged_df['Total Value'].sum()
            if total_value_sum != 0:
                total_avg_dividend_yield = (total_dividend_sum / total_value_sum) * 100
            else:
                total_avg_dividend_yield = None
            merged_df.loc[0, 'Total Avg Dividend Yield'] = total_avg_dividend_yield
            merged_df['Total Avg Dividend Yield'] = merged_df['Total Avg Dividend Yield'].where(merged_df.index == 0, None)
            
            st.write(merged_df)

            st.sidebar.download_button(
                label="Download Merged Data",
                data=merged_df.to_csv(index=False),
                file_name='merged_data.csv',
                mime='text/csv'
            )

if __name__ == '__main__':
    asyncio.run(main())
