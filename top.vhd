library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;

entity top is
  port (
    clk          : in  std_logic;
    reset        : in  std_logic;
    --
    data_in      : in  std_logic_vector(7 downto 0);
    data_in_vld  : in  std_logic;
    --
    data_out     : out std_logic_vector(7 downto 0);
    data_out_vld : out std_logic
    );
end entity;

architecture rtl of top is

  signal addr    : std_logic_vector(15 downto 0);
  signal wr_data : std_logic_vector(31 downto 0);
  signal wr_en   : std_logic;
  signal rd_en   : std_logic;
  signal rd_data : std_logic_vector(31 downto 0);
  signal rd_ack  : std_logic;

begin

  u_fsm : entity work.register_fsm
    port map (
      clk          => clk,
      reset        => reset,
      data_in      => data_in,
      data_in_vld  => data_in_vld,
      data_out     => data_out,
      data_out_vld => data_out_vld,
      addr         => addr,
      wr_data      => wr_data,
      wr_en        => wr_en,
      rd_en        => rd_en,
      rd_data      => rd_data,
      rd_ack       => rd_ack
      );

  u_mem : entity work.memory_model
    port map (
      clk     => clk,
      reset   => reset,
      addr    => addr,
      wr_data => wr_data,
      wr_en   => wr_en,
      rd_en   => rd_en,
      rd_data => rd_data,
      rd_ack  => rd_ack
      );

end architecture rtl;