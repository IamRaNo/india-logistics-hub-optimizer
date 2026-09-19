-- Active: 1745477253100@@127.0.0.1@3306@logistics_hub_db
show tables;

select * from way_bill_data;

select * from population_data;

select * from gsdp_data;

-- Clean New Table Creation For way_bill_data
create table bills as
select 
    state_code as `code`,
    trim(lower(state_name)) as state,
    `year`,
    `month`,
    intra_suplliers_no as intra_suppliers,
    intra_bill_no as intra_bills,
    round(intra_asset_val,2) as intra_assets,
    inter_out_suplliers_no as inter_out_suppliers,
    inter_out_bill_no as inter_out_bills,
    round(inter_out_asset_val,2) as inter_out_assets,
    inter_in_suplliers_no as inter_in_suppliers,
    inter_in_bill_no as inter_in_bills,
    round(inter_in_asset_val,2) as inter_in_assets
from way_bill_data;

-- Clean New Table For gsdp_data
create table gsdp as
select 
    replace(replace(replace(trim(lower(`state/ut`)),"*",""),"*(ut)",""),"-UT","") as state,
    round(`2018-19`,2) as `2018-19`,
    round(`2019-20`,2) as `2019-20`,
    round(`2020-21`,2) as `2020-21`,
    round(`2021-22`,2) as `2021-22`,
    round(`2022-23`,2) as `2022-23`,
    round(`2023-24`,2) as `2023-24`
from gsdp_data;


-- Clean New Table For population_data
create table `population` as
select 
    trim(replace(replace(trim(lower(`state/ut`)), '*(ut)', ''), '*', '')) as `state`,
    `2018`,
    `2019`,
    `2020`,
    `2021`,
    `2022`,
    `2023`,
    `2024`,
    `2025`,
    `2026`
from population_data;


SELECT * from bills where `month` = 3 and `year` = 2025;


select * from bills;
create view forecasting_data as
with totaled as(
select
    `state`,
    `year`,
    `month`,
    concat(`year`,"-",lpad(`month`,'2',0)) as `date`,
    (intra_bills+inter_out_bills+inter_in_bills) as bill_volume,
    round((intra_assets+inter_out_assets+inter_in_assets),2) as bill_amount
from bills
order by `year`, `month`
)
select `state`,`date`,bill_volume, bill_amount,
round(avg(bill_volume) over(partition by `state` order by `year`,`month` rows between 2 preceding and current row),2) as avg_bill_3m,
round(avg(bill_amount) over(partition by `state` order by `year`,`month` rows between 2 preceding and current row),2) as avg_amount_3m
from totaled;
