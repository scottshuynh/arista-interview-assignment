library std;
use std.textio.all;

library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;

use std.env.finish;

entity tb_vhdl_assignment_simple is
end entity tb_vhdl_assignment_simple;

architecture test of tb_vhdl_assignment_simple is

  constant CLK_PERIOD_C : time := 8 ns;

  -- Procedure to emit a byte sequence
  procedure play_sequence(signal clk          : in  std_logic;
                          signal data_out     : out std_logic_vector(7 downto 0);
                          signal data_out_vld : out std_logic;
                          signal checked      : in  std_logic;
                          data_seq            : in  std_logic_vector)
  is
    variable bit_idx : integer := 0;
  begin
    while bit_idx < data_seq'length loop
      data_out     <= data_seq(bit_idx to bit_idx+7);
      data_out_vld <= '1';
      bit_idx      := bit_idx + 8;
      wait until rising_edge(clk);
    end loop;
    -- Wait until the response is checked
    data_out_vld <= '0';
    wait until rising_edge(clk) and checked = '1';
  end procedure;

  -- Procedure to check a byte sequence
  procedure check_sequence(signal clk         : in  std_logic;
                           signal data_in     : in  std_logic_vector(7 downto 0);
                           signal data_in_vld : in  std_logic;
                           signal checked     : out std_logic;
                           data_seq           : in  std_logic_vector)
  is
    variable bit_idx : integer := 0;
  begin
    while bit_idx < data_seq'length loop
      wait until rising_edge(clk) and data_in_vld = '1';
      if data_seq(bit_idx to bit_idx+7) /= data_in then
        assert false
          report "Data mismatch. Expected 0x" & to_hstring(data_seq(bit_idx to bit_idx+7)) & ", received 0x" & to_hstring(data_in) & "."
          severity error;
        exit;
      end if;
      bit_idx := bit_idx + 8;
    end loop;
    wait until rising_edge(clk) and data_in_vld = '0';
    checked <= '1';
    wait until rising_edge(clk);
    checked <= '0';
    wait until rising_edge(clk);
  end procedure;


  -- UUT Interface Signals
  signal clk          : std_logic;
  signal reset        : std_logic;
  signal data_in      : std_logic_vector(7 downto 0) := (others => '0');
  signal data_in_vld  : std_logic                    := '0';
  signal data_out     : std_logic_vector(7 downto 0);
  signal data_out_vld : std_logic;

  -- TB Signals
  signal checked : std_logic := '0';

begin

  ------------------------------------------------------------------------------
  -- Unit Under Test
  ------------------------------------------------------------------------------
  uut : entity work.top
    port map (
      clk          => clk,
      reset        => reset,
      data_in      => data_in,
      data_in_vld  => data_in_vld,
      data_out     => data_out,
      data_out_vld => data_out_vld
      );

  ------------------------------------------------------------------------------
  -- Clock
  ------------------------------------------------------------------------------
  p_stim_clk : process
  begin
    clk <= '1';
    wait for CLK_PERIOD_C/2;
    clk <= '0';
    wait for CLK_PERIOD_C/2;
  end process;

  ------------------------------------------------------------------------------
  -- Reset
  ------------------------------------------------------------------------------
  p_stim_reset : process
  begin
    reset <= '0';
    for i in 0 to 9 loop
      wait until rising_edge(clk);
    end loop;
    reset <= '1';
    wait until rising_edge(clk);
    reset <= '0';
    wait;
  end process;

  ------------------------------------------------------------------------------
  -- Data Input Stimulus
  ------------------------------------------------------------------------------
  p_stim : process
  begin
    -- Wait 10 cycles after reset
    wait until rising_edge(clk) and reset = '1';
    for i in 0 to 9 loop
      wait until rising_edge(clk);
    end loop;

    -- Run through a list of sequences
    play_sequence(clk, data_in, data_in_vld, checked, x"e7_13_00_00_00_03");
    play_sequence(clk, data_in, data_in_vld, checked, x"e7_13_00_00_00_e7_e7");
    play_sequence(clk, data_in, data_in_vld, checked, x"e7_23_00_00_00_02_aa_e7_e7_55_aa_e7_13_00_00_00_02");
    play_sequence(clk, data_in, data_in_vld, checked, x"e7_23_00_00_00_01_aa_e7_55_e7_13_00_00_00_01");

    -- Done, wait here indefinitly
    wait;
  end process;
  
  ------------------------------------------------------------------------------
  -- Data Checking
  ------------------------------------------------------------------------------
  p_chk : process
  begin
    -- Wait 1 cycle after after reset
    wait until rising_edge(clk) and reset = '1';
    wait until rising_edge(clk);

    -- Check through a list of sequences
    check_sequence(clk, data_out, data_out_vld, checked, x"e7_03_10_20_30_40");
    check_sequence(clk, data_out, data_out_vld, checked, x"e7_03_de_ad_be_ef");
    check_sequence(clk, data_out, data_out_vld, checked, x"e7_03_aa_e7_e7_55_aa");
    check_sequence(clk, data_out, data_out_vld, checked, x"e7_03_89_ab_cd_e7_e7");

    -- Done.
    report "Simulation Finished";
    finish;
  end process;


  ------------------------------------------------------------------------------
  -- Test Timout
  ------------------------------------------------------------------------------
  p_timeout : process
  begin
    wait for 15 us;
    assert false
      report "Simulation FAIL - Timout"
      severity failure;
  end process;

end architecture test;