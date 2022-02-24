-- PROCEDURE: public.update_valuations_new(integer)

-- DROP PROCEDURE public.update_valuations_new(integer);

CREATE OR REPLACE PROCEDURE public.update_valuations_new(
	playerid integer)
LANGUAGE 'plpgsql'
AS $BODY$
declare
		cf_calc double precision default 0.00;
		context record;
		player record;
		company record;
		ir record;
		match record;
		pid integer default 0;
		battingsr double precision default 0.00;
		bowlingsr double precision default 0.00;
		bowlingaverage double precision default 0.00;
		rpo double precision default 0.00;
		price double precision default 0.00;
		cfbattingsr double precision default 100.00;
		cfbatting_average double precision default 0.00;
		cfbowlingsr double precision default 0.00;
		cfbowling_average double precision default 0.00;
		cfeconomy double precision default 10.00;
		cf double precision default 0.00;
		basecmp double precision default 0.00;
		newcmp double precision default 0.00;
		oldcmp double precision default 0.00;
		formcmp double precision default 0.00;
		pricechange double precision default 0.00;
		newvalue double precision default 0.00;
		hundreds integer default 0;
		fifties integer default 0;
		fourfers integer default 0;
		fifers integer default 0;
		sixfers integer default 0;
		
		cur_match cursor for
		select * from market_match where player_id = playerid;
		
		cur_record cursor for
		select * from market_investmentrecord where company_id = playerid;
		
	
	begin
		open cur_match;
		--Add these columns to market_match once IPL is over
		fifties = 0;
		hundreds = 0;
		fourfers = 0;
		fifers = 0;
		sixfers = 0;
		loop
			fetch cur_match into match;
			exit when not found;
			if match.runs >= 100 then
				hundreds = hundreds + 1;
			elsif match.runs < 100 and match.runs >= 50 then
				fifties = fifties + 1;
			end if;
			
			if match.wickets = 5 then
				fifers = fifers + 1;
			elsif match.wickets = 4 then
				fourfers = fourfers + 1;
			end if;
		end loop;
		
		close cur_match;
		
		select
			count(*) as cfmatches,
			sum(runs) as cfruns,
			sum(balls_faced) as cfballs_faced,
			sum(fours) as cffours,
			sum(sixes) as cfsixes,
			sum(catches) as cfcatches,
			sum(stumpings) as cfstumpings,
			sum(balls_bowled) as cfballs_bowled,
			sum(runs_conceded) as cfruns_conceded,
			sum(wickets) as cfwickets,
			sum(runouts) as cfrunouts,
			sum(dismissed) as cfdismissed
		into player
		from market_match
		where player_id = playerid
		group by player_id;
		
		if player.cfmatches is null then
			player.cfmatches = 0;
			player.cfruns = 0;
			player.cfballs_faced = 0;
			player.cffours = 0;
			player.cfsixes = 0;
			player.cfcatches = 0;
			player.cfstumpings = 0;
			player.cfballs_bowled = 0;
			player.cfruns_conceded = 0;
			player.cfwickets = 0;
			player.cfrunouts = 0;
			player.cfdismissed = 0;
		end if;

		
		--Sum(cmpchange) would effectively give us the value of currentform
		select sum(cmpchange) as change, company_id
		into context
		from market_companycmprecord
		where company_id = playerid
		and extract(day from current_timestamp - updated) < 7
		group by company_id;
		
		if context.change is null then
			context.change = 0.00;
			context.company_id = playerid;
		end if;
		
		--Base cmp
		select cmp into basecmp
		from market_companycmprecord
		where company_id = playerid
		order by updated desc
		fetch first 1 row only;
		
		--Calculate the current form value
		
		if player.cfballs_faced <> 0 then
			cfbattingsr = (cast(player.cfruns as double precision)/cast(player.cfballs_faced as double precision))*100.00;
		end if;
		raise notice 'CF Batting SR: %  %', cfbattingsr, E'\n';
		
		if player.cfballs_bowled <> 0 then
			cfeconomy = cast(player.cfruns_conceded as double precision)/(cast(player.cfballs_bowled as double precision)/6.00);
		end if;
		raise notice 'CF Economy: %  %', cfeconomy, E'\n';
		
		if player.cfdismissed <> 0 then
			cfbatting_average = cast(player.cfruns as double precision)/cast(player.cfdismissed as double precision);
		else
			cfbatting_average = cast(player.cfruns as double precision) + 20.00;
		end if;
		raise notice 'CF Batting average: %  %', cfbatting_average, E'\n';

		cf_calc = 0.00;
		
		cf_calc = (player.cfruns * 5)
			+
			(player.cfballs_faced * 2)
			+
			(player.cffours * 5)
			+
			(player.cfsixes * 15)
			+
			(player.cfcatches * 10)
			+
			(player.cfstumpings * 10)
			+
			(player.cfballs_bowled * 5)
			--+
			--(player.cfruns_conceded * )
			+
			(player.cfwickets * 100)
			+
			(player.cfrunouts * 10)
			+
			(cfbattingsr * 50)
			--((cfbattingsr - 100) * 75)
			--+
			--((cfbatting_average - 20) * 100)
			--+
			--((24 - cfbowlingsr) * 100)
			--+
			--((50 - cfbowling_average) * 50)
			+
			((10 - cfeconomy) * 500)
			+
			(fifties * 100)
			+
			(hundreds * 300)
			+
			(fourfers * 100)
			+
			(fifers * 200);
			
			cf_calc = cf_calc * 1.25; --This makes current form 10% more valid than normal stats
			cf_calc = cf_calc - (player.cfdismissed * 100);

			
			cf = cf_calc;
			raise notice 'Current form: %  %', cf, E'\n';
			update market_playervaluations
			set current_form = cf
			where id = playerid;
			
			select system_valuation as sysval, current_form as curform 
			into company 
			from market_playervaluations 
			where id = playerid;
			
			newcmp = (company.sysval + company.curform)/100000;
			
			if newcmp < 1.00 then
				newcmp = 1.00;
			end if;
			
			raise notice 'NEW CMP: %  %', newcmp, E'\n';
			
			formcmp = company.curform/100000; > # of each player shares
			
			--This logic is to indicate how much the player's price has changed in the last 24 hours
			--Ball by ball price change would show a drop in price if a player plays a dot ball even after scoring a century
-- 			select cmp into oldcmp
-- 			from market_companycmprecord 
-- 			where company_id = playerid
-- 			and extract(hour from (current_timestamp - updated)) <= 24
-- 			order by timestamp asc
-- 			fetch first 1 row only;

			select cmp into oldcmp from market_company where id = playerid;
			
			pricechange = newcmp - oldcmp;
			
			if pricechange is not null then
				pricechange = pricechange;
			else
				pricechange = 0;
			end if;
			raise notice 'Price Change: %  %', pricechange, E'\n';
			--Updating the cmp in the Company table
			update market_company
 			set cmp = newcmp, change = pricechange, updated = current_timestamp, cfcmp = formcmp
 			where id = playerid;
			
			--This is redundant, but a few players' prices seem to be dropping below 1.00 unexpectedly
			update market_company
			set cmp = 1.00
			where cmp < 1.00;
			
			--Inserting the changed cmp into the Company CMP record table
			insert into market_companycmprecord (cmp, contextcmp, cmpchange, timestamp, updated, company_id, event) 
			values (newcmp, 0.0, pricechange, current_timestamp, current_timestamp, playerid, 'NA');
			-- not necessay
			--Updating gain_loss in investmentrecord
			-- open cur_record;
		
			-- loop
			
			-- 	fetch cur_record into ir;
			-- 	exit when not found;
				
			-- 	newvalue = newcmp * ir.stocks;
				
			-- 	update market_investmentrecord
			-- 	set gain_loss = newvalue - investment
			-- 	where current of cur_record;
			
			-- end loop;
	
			-- close cur_record;

	end;
$BODY$;


