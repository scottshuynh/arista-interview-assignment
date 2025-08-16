library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;

entity memory_model is
  port (
    clk   : in std_logic;
    reset : in std_logic;
    --
    addr    : in  std_logic_vector(15 downto 0);
    wr_data : in  std_logic_vector(31 downto 0);
    wr_en   : in  std_logic;
    rd_en   : in  std_logic;
    rd_data : out std_logic_vector(31 downto 0);
    rd_ack  : out std_logic
  );
end entity memory_model;

architecture beh of memory_model is
  ------------------------------------------------------------------------------
  -- Utility types and functions that would typically live in some utility pkg.
  ------------------------------------------------------------------------------
  type array_slv_t is array(natural range <>) of std_logic_vector;

  function to_slv (val : integer; slv_w : natural) return std_logic_vector is
    variable result : std_logic_vector(slv_w-1 downto 0);
  begin
    result := std_logic_vector(to_signed(val, slv_w));
    return result;
  end function;

  function ceil_divide(n : natural; d : natural) return natural is
    variable result : natural;
  begin
    result := (n + d - 1) / d;
    return result;
  end function;

  function ceil_log2(num : natural) return natural is
    variable divide : natural := num;
    variable result : natural := 0;
  begin
    l_divide : while (divide /= 1) loop
      divide := ceil_divide(divide, 2);
      if (divide >= 1) then
        result := result + 1;
      end if;
    end loop;
    return result;
  end function;

  ------------------------------------------------------------------------------

  constant ADDR_W      : natural := addr'length;
  constant DATA_W      : natural := wr_data'length;
  constant LAST_ADDR   : natural := 231;
  constant OPT_ADDR_W  : natural := ceil_log2(LAST_ADDR);
  constant OPT_RAM_LEN : natural := 2**OPT_ADDR_W;

  constant INIT_RAM : array_slv_t(0 to OPT_RAM_LEN-1)(DATA_W-1 downto 0) := (
      0      => x"01234567",
      1      => x"89abcde7",
      2      => x"0a0b0c0d",
      3      => x"10203040",
      231    => x"deadbeef",
      others => (others => '0'));

  constant VALID_RAM_ADDRS : std_logic_vector(OPT_RAM_LEN-1 downto 0) := (
      0      => '1',
      1      => '1',
      2      => '1',
      3      => '1',
      231    => '1',
      others => '0');

  signal ram      : array_slv_t(0 to OPT_RAM_LEN-1)(DATA_W-1 downto 0) := INIT_RAM;
  signal ram_addr : unsigned(OPT_ADDR_W-1 downto 0);

  constant NUM_RD_PIPELINE : natural                                                := 2;
  signal rd_data_regs      : array_slv_t(0 to NUM_RD_PIPELINE-1)(DATA_W-1 downto 0) := (others => (others => '0'));
  signal rd_ack_regs       : std_logic_vector(NUM_RD_PIPELINE-1 downto 0)           := (others => '0');

  function is_valid_ram_addr(addr : unsigned) return boolean is
  begin
    return VALID_RAM_ADDRS(to_integer(addr)) = '1';
  end function;

begin

  -- Truncate unused MSBs for the optimised address
  ram_addr <= resize(unsigned(addr), OPT_ADDR_W);

  p_clk : process (clk)
  begin
    if rising_edge(clk) then
      -- RAM write control
      if (wr_en = '1') then
        if (is_valid_ram_addr(ram_addr)) then
          if (or addr(addr'high downto OPT_ADDR_W) = '0') then
            ram(to_integer(unsigned(ram_addr))) <= wr_data;
          end if;
        end if;
      end if;

      -- RAM read control
      rd_ack_regs(0) <= '0';
      if (rd_en = '1') then
        if (is_valid_ram_addr(ram_addr)) then
          if (or addr(addr'high downto OPT_ADDR_W) = '0') then
            rd_data_regs(0) <= ram(to_integer(unsigned(ram_addr)));
            rd_ack_regs(0)  <= '1';
          end if;
        end if;
      end if;

      l_sr_rd : for IDX in 1 to NUM_RD_PIPELINE-1 loop
        rd_data_regs(IDX) <= rd_data_regs(IDX-1);
        rd_ack_regs(IDX)  <= rd_ack_regs(IDX-1);
      end loop;

      if (reset = '1') then
        rd_ack_regs <= (others => '0');
        ram         <= INIT_RAM;
      end if;
    end if;
  end process;

  rd_data <= rd_data_regs(0);
  rd_ack  <= rd_ack_regs(0);

  -- NOTE: Replace above output assignments with these to alleviate timing
  -- rd_data <= rd_data_regs(NUM_RD_PIPELINE-1);
  -- rd_ack  <= rd_ack_regs(NUM_RD_PIPELINE-1);

end architecture beh;
