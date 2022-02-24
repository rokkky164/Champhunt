-- PROCEDURE: public.calculate_valuations_onetime()

-- DROP PROCEDURE public.calculate_valuations_onetime();

CREATE OR REPLACE PROCEDURE public.calculate_valuations_onetime(
	)
LANGUAGE 'plpgsql'
AS $BODY$
declare
		valuation_calc double precision default 0.00;
		bowlingratio double precision default 1.00;
		player record;
		cur_player cursor for 
				select *
				from market_playerstats where id <> 0;
		bbiwickets integer default 0;
		bbiruns integer default 0;
		highestruns integer default 0;
		isnotout integer default 0;
		pid integer default 0;
		staging text default '';
		battingsr double precision default 0.00;
		bowlingsr double precision default 0.00;
		bowlingaverage double precision default 0.00;
		rpo double precision default 0.00;
		system_valuation double precision default 0.00;
		price double precision default 0.00;
		battingavg double precision default 0.00;
		player_code text default '';
		first_name text default '';
		last_name text default '';
		center integer default 0;
	
	begin
		--Inserting a blank player into market_playerstats
		INSERT INTO market_playerstats (ipl_team, id, name, full_name, dob, pob, playing_role, batting_style, bowling_style, matches, batting_innings, notouts, runs, highest, batting_average, balls_faced, batting_sr, hundreds, fifties, fours, sixes, catches, stumpings, bowling_innings, balls_bowled, runs_conceded, wickets, bbi, bbm, bowling_average, economy, bowling_sr, fourfers, fifers, tenfers) VALUES ('NA',1,'None None','None None' ,'NA','NA','NA','NA','NA',0,0,0,0,'0',0.00,0,0.00,0,0,0,0,0,0,0,0,0,0,'0','0',0.00,0.00,0.00,0,0,0);

	--For IPL
  		update market_playerstats set ipl_team = 'Chennai Super Kings' where ipl_team like '%Chennai%';
  		update market_playerstats set ipl_team = 'Delhi Capitals' where ipl_team like '%Delhi%';
  		update market_playerstats set ipl_team = 'Punjab Kings' where ipl_team like '%Punjab%';
  		update market_playerstats set ipl_team = 'Kolkata Knight Riders' where ipl_team like '%Kolkata%';
  		update market_playerstats set ipl_team = 'Mumbai Indians' where ipl_team like '%Mumbai%';
  		update market_playerstats set ipl_team = 'Rajasthan Royals' where ipl_team like '%Rajasthan%';
  		update market_playerstats set ipl_team = 'Royal Challengers Bangalore' where ipl_team like '%Bangalore%';
  		update market_playerstats set ipl_team = 'Sunrisers Hyderabad' where ipl_team like '%Hyderabad%';

	--For LPL
-- 		update market_playerstats set ipl_team = 'Colombo Kings' where ipl_team like '%Colombo%';
-- 		update market_playerstats set ipl_team = 'Dambulla Viiking' where ipl_team like '%Dambulla%';
-- 		update market_playerstats set ipl_team = 'Galle Gladiators' where ipl_team like '%Galle%';
-- 		update market_playerstats set ipl_team = 'Jaffna Stallions' where ipl_team like '%Jaffna%';
-- 		update market_playerstats set ipl_team = 'Kandy Tuskers' where ipl_team like '%Kandy%';

	--For BBL
-- 	update market_playerstats set ipl_team = 'Adelaide Strikers' where ipl_team like '%Adelaide%';
-- 	update market_playerstats set ipl_team = 'Brisbane Heat' where ipl_team like '%Brisbane%';
-- 	update market_playerstats set ipl_team = 'Hobart Hurricanes' where ipl_team like '%Hobart%';
-- 	update market_playerstats set ipl_team = 'Melbourne Renegades' where ipl_team like '%Melbourne Renegades%';
-- 	update market_playerstats set ipl_team = 'Melbourne Stars' where ipl_team like '%Melbourne Stars%';
-- 	update market_playerstats set ipl_team = 'Perth Scorchers' where ipl_team like '%Perth%';
-- 	update market_playerstats set ipl_team = 'Sydney Sixers' where ipl_team like '%Sydney Sixers%';
-- 	update market_playerstats set ipl_team = 'Sydney Thunder' where ipl_team like '%Sydney Thunder%';
	
		
		--Calculate valuations functionality begins
		open cur_player;
		
		loop
		
			fetch cur_player into player;
			exit when not found;
			
			if player.bbi = '0' then
				bbiwickets = 0;
				bbiruns = 32;
			else
				--staging = substring(player.bbi from '([0-9]{1})');
				bbiwickets = cast(substring(player.bbi from '([0-9]{1})') AS INTEGER);
				--staging = substring(player.bbi from 3);
				bbiruns = cast(substring(player.bbi from 3) as INTEGER);
			end if;
			
			if player.highest = '0' then
				isnotout = 0;
				highestruns = 0;
			else
				if substring(player.highest from length(player.highest)) = '*' then
					isnotout = 1;
					highestruns = cast(substring(player.highest, 1, length(player.highest)-1) as INTEGER);
				else
					isnotout = 0;
					highestruns = cast(substring(player.highest, 1, length(player.highest)) as INTEGER);
				end if;
			end if;
			
			--If you want to move to a 'distance from 100' model, write an if statement to assign battingsr = 100.00 if the player's batting_sr is 0.00
			battingsr = player.batting_sr;
			
			--If you want to move to a 'distance from 20' model, write an if statement to assign battingavg=20.00 if the player's battingavg is 0.00
			battingavg = player.batting_average;
			
			if player.bowling_sr = 0.00 then
				bowlingsr = 24.00;
			else
				bowlingsr = player.bowling_sr;
			end if;
			
			if player.bowling_average = 0.00 then
				bowlingaverage = 50.00;
			else
				bowlingaverage = player.bowling_average;
			end if;
			
			if player.economy = 0.00 then
				rpo = 10.00;
			else
				rpo = player.economy;
			end if;
			
			if player.matches > 0 then
				bowlingratio = player.bowling_innings/player.matches;
			else
				bowlingratio = 1.00;
			end if;
			
			valuation_calc = 0;
			
			valuation_calc = (player.matches * 5)
			+
			(player.batting_innings * 5)
			+
			(player.notouts * 10)
			+
			(player.runs * 5)
			+
			(highestruns * 10)
			+
			(isnotout * 10)
			+
			(battingavg * 50)
-- 			+
-- 			((battingavg - 20.00) * 100)
			+
			(player.balls_faced * 2)
			+
			(battingsr * 50)
-- 			+
-- 			((battingsr - 100.00) * 50)
			+
			(player.hundreds * 300)
			+
			(player.fifties * 100)
			+
			(player.fours * 5)
			+
			(player.sixes * 15)
			+
			(player.catches * 10)
			+
			(player.stumpings * 10)
			+
			(player.bowling_innings * 5)
			+
			(player.balls_bowled * 5)
			--+
			--(player.runs_conceded * )
			+
			(player.wickets * 100)
			+
			(bbiwickets * 200)
			+
			((32 - bbiruns) * 10)
			+
			((50.00 - bowlingaverage) * bowlingratio * 50)  --Bowling ratio/batting ratio gives us an indication on whether the player is a batsman/bowler/allrounder
			+
			((10.00 - rpo) * bowlingratio * 500)
			+
			((24.00 - bowlingsr) * bowlingratio * 100)
			+
			(player.fourfers * 100)
			+
			(player.fifers * 200)
			+
			(player.tenfers * 500);
			
			pid = player.id;
			
			--This is for after the table has been populated
			--update market_playervaluations
			--set valuation = valuation_calc
			--where id = pid;
			
			--update market_company
			--set ...
			--where id = pid;
			
			--if statement to incorporate players with no last name
			if player.name not like '% %' then
				center = length(player.name)/2;
				first_name = substring(player.name,1,cast(center as integer));
				last_name = substring(player.name, cast(center as integer)+1);
			else
				first_name = substring(player.name, 1, position(' ' in player.name)-1);
				last_name = substring(player.name, position(' ' in player.name)+1);
			end if;
			
			--Accounting for those cases where the player's first name is less than 4 letters. E.g. JOS BUTTLER, KM ASIF, TOM CURRAN, SAM CURRAN etc.
			if length(first_name) >= 4 then
				player_code = upper(substring(first_name, 1, 4)) || upper(substring(last_name, 1, 3));
				raise notice 'Player code: %  %', player_code, E'\n';
			else
				player_code = upper(substring(first_name, 1, length(first_name)-1)) || upper(substring(last_name, 1, 3));
				raise notice 'Player code: %  %', player_code, E'\n';
			end if;
			
			--To account for names like Naveen-ul-Haq
			if player_code like '%-%' then
				player_code = substring(player_code, 1, position('-' in player_code)-1) || substring(player_code, position(' ' in player_code)+1,3);
			end if;
			--OR
			if player_code like '% %' then
				player_code = substring(player_code, 1, position(' ' in player_code)-1) || substring(player_code, position(' ' in player_code)+1,3);
				raise notice 'Player code: %  %', player_code, E'\n';
			end if;
			
			if player_code like '% %' then
				player_code = substring(player_code, 1, position(' ' in player_code)-1);
				raise notice 'Player code: %  %', player_code, E'\n';
			end if;
			
			--Exceptions
			--KULDYAD - KULDIP YADAV AND KULDEEP YADAV
			if player_code like '%KULDYAD%' then
				player_code = upper(substring(first_name, 1, 5)) || upper(substring(last_name, 1, 3));
				raise notice 'Player code: %  %', player_code, E'\n';
			end if;
			--MOHSHA - Mohammad Shahzad and Mohammad Shami
			if player_code like '%MOHASHA%' then
				player_code = upper(substring(first_name, 1, 3)) || upper(substring(last_name, 1, 4));
				raise notice 'Player code: %  %', player_code, E'\n';
			end if;
			
			system_valuation = valuation_calc * 100;
			price = system_valuation/100000;
			insert into market_playervaluations(id, name, team, system_valuation, current_form, mkt_qty, company_id)
			values (player.id, upper(player.name), player.ipl_team, system_valuation, 0.00, 100000, player.id);

--cap has been removed
--asp has been removed
-- 			insert into market_company (id, code, name, mkt_qty, cap, cmp, change, cap_type, stocks_bought, industry, timestamp, updated, cfcmp, asp)
--  			values (player.id, player_code, upper(player.name), 100000, system_valuation, price, 0, 'NA', 0, player.playing_role, current_timestamp, current_timestamp, 0.00, 0.00);
			insert into market_company (id, code, name, quantity, cmp, change, cap_type, stocks_bought, industry, first_loading_time, updated, cfcmp)
 			values (player.id, player_code, upper(player.name), 100000, price, 0, 'NA', 0, player.playing_role, current_timestamp, current_timestamp, 0.00);
			
			raise notice 'Player: %  %', player.name, E'\n';
			raise notice 'Valuation: %  %', valuation_calc, E'\n';
			raise notice 'CMP: %  %', price, E'\n';

		end loop;
		
		close cur_player;
		
		
	end;
$BODY$;


