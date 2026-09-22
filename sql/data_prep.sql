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


select * from gsdp limit 5;

select * from bills limit 5;

with temp as (
select `state`, `year`,
round((sum(intra_assets) + sum(inter_out_assets) +sum(inter_in_assets)),2)as total_assets
from bills
group by 1,2
)
select 
 state,
  sum(case when year = 2018 then total_assets end) as `2018-19`,
  sum(case when year = 2019 then total_assets end) as `2019-20`,
  sum(case when year = 2020 then total_assets end) as `2020-21`,
  sum(case when year = 2021 then total_assets end) as `2021-22`,
  sum(case when year = 2022 then total_assets end) as `2022-23`
from temp
where `state` not in ('daman and diu', 'dadra and nagar haveli','lakshadweep')
group by state;

select `state` from gsdp;

update gsdp set state = 'andaman and nicobar' where state = 'andaman & nicobar islands';
update gsdp set state = 'jammu and kashmir' where state = 'jammu & kashmir-ut';

create view bill_growth as
with bills_agg as(
    select 
 state,
  sum(case when year = 2018 then total_assets end) as `2018-19`,
  sum(case when year = 2019 then total_assets end) as `2019-20`,
  sum(case when year = 2020 then total_assets end) as `2020-21`,
  sum(case when year = 2021 then total_assets end) as `2021-22`,
  sum(case when year = 2022 then total_assets end) as `2022-23`
  from (
    select `state`, `year`,
    round((sum(intra_assets) + sum(inter_out_assets) +sum(inter_in_assets)),2)as total_assets
    from bills
    group by 1,2
  ) temp
  where `state` not in ('daman and diu', 'dadra and nagar haveli','lakshadweep')
  group by state
),
bills_growth as(
    select
        `state`,
        round((`2019-20` - `2018-19`) / `2018-19` * 100, 2) as `18/19-19/20`,
        round((`2020-21` - `2019-20`) / `2019-20` * 100, 2) as `19/20-20/21`,
        round((`2021-22` - `2020-21`) / `2020-21` * 100, 2) as `20/21-21/22`,
        round((`2022-23` - `2021-22`) / `2021-22` * 100, 2) as `21/22-22/23`
    from bills_agg
)
select * from bills_growth;



select * from bills_growth;
select * from gsdp;
create view gsdp_growth as
select
    state,
    round((`2019-20` - `2018-19`) / `2018-19` * 100, 2) as `18/19-19/20`,
    round((`2020-21` - `2019-20`) / `2019-20` * 100, 2) as `19/20-20/21`,
    round((`2021-22` - `2020-21`) / `2020-21` * 100, 2) as `20/21-21/22`,
    round((`2022-23` - `2021-22`) / `2021-22` * 100, 2) as `21/22-22/23`
from gsdp;


select * from gsdp_growth;
select * from bill_growth;


