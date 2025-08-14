library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;

entity register_fsm is
  port (
    clk   : in std_logic;
    reset : in std_logic;
    --
    data_in      : in  std_logic_vector(7 downto 0);
    data_in_vld  : in  std_logic;
    data_out     : out std_logic_vector(7 downto 0);
    data_out_vld : out std_logic;
    --
    addr    : out std_logic_vector(15 downto 0);
    wr_data : out std_logic_vector(31 downto 0);
    wr_en   : out std_logic;
    rd_en   : out std_logic;
    rd_data : in  std_logic_vector(31 downto 0);
    rd_ack  : in  std_logic);
end register_fsm;

architecture rtl of register_fsm is
  ------------------------------------------------------------------------------
  -- Utility types and functions that would typically live in some utility pkg.
  ------------------------------------------------------------------------------
  type array_slv_t is array(natural range <>) of std_logic_vector;

  function to_flat_slv (arr_slv : array_slv_t) return std_logic_vector is
    constant ARR_LEN : natural := arr_slv'length;
    constant ELEM_W  : natural := arr_slv(0)'length;
    variable result  : std_logic_vector(ARR_LEN*ELEM_W-1 downto 0);
  begin
    for IDX in 0 to ARR_LEN-1 loop
      result((IDX+1)*ELEM_W-1 downto (IDX)*ELEM_W) := arr_slv(IDX);
    end loop;
    return result;
  end function;

  function to_array_slv (flat_slv : std_logic_vector; elem_w : natural; arr_len : natural) return array_slv_t is
    variable result : array_slv_t(0 to arr_len-1)(elem_w-1 downto 0);
  begin
    assert (flat_slv'length = elem_w * arr_len)
      report "Unable to transform a slv of length " & integer'image(flat_slv'length)
      & " into a " & integer'image(arr_len) & "x" &integer'image(elem_w) & " array."
      severity FAILURE;
    for IDX in 0 to ARR_LEN-1 loop
      result(IDX) := flat_slv((IDX+1)*elem_w-1 downto IDX*elem_w);
    end loop;
    return result;
  end function;

  function reverse_array (arr_slv : array_slv_t) return array_slv_t is
    variable result : array_slv_t(arr_slv'range)(arr_slv(arr_slv'low)'range);
  begin
    l_reverse : for IDX in arr_slv'range loop
      result(IDX) := arr_slv(arr_slv'left + arr_slv'right - IDX);
    end loop;
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

  function to_hex_string(slv : std_logic_vector) return string is
    constant HEX_CHARS  : string  := "0123456789ABCDEF";
    constant STRING_LEN : natural := (slv'length + 3) / 4;
    constant NIBBLE_W   : natural := 4;

    constant SLV_NIBBLE_ALIGNED : std_logic_vector(STRING_LEN*NIBBLE_W-1 downto 0) := std_logic_vector(resize(unsigned(slv), STRING_LEN*NIBBLE_W));

    variable current_nibble : unsigned(NIBBLE_W-1 downto 0);
    variable result         : string(1 to STRING_LEN);
  begin
    for IDX in 0 to STRING_LEN-1 loop
      current_nibble := unsigned(slv((IDX+1)*NIBBLE_W-1 downto IDX*NIBBLE_W));
      result(IDX+1)  := HEX_CHARS(to_integer(current_nibble+1));
    end loop;
    return result;
  end function;

  ------------------------------------------------------------------------------

  constant BYTE_W     : natural := data_in'length;
  constant ADDR_W     : natural := addr'length;
  constant DATA_W     : natural := wr_data'length;
  constant RD_LATENCY : natural := 4;

  type cmd_t is (CMD_READ, CMD_WRITE, CMD_READ_DATA, CMD_BREAK, ESCAPE, CMD_NULL, INVALID);
  type reg_fsm_t is (AWAIT_ESC, PARSE_CMD, PARSE_ADDR, PARSE_WRITE_DATA);
  type rd_resp_fsm_t is (AWAIT_RD_EN, AWAIT_RD_ACK, OUTPUT_CMD_READ_DATA, OUTPUT_RD_RESP, PIPE_RD_DATA_BYTES_IDX, OUTPUT_BREAK);

  function to_cmd (slv : std_logic_vector) return cmd_t is
    variable result : cmd_t;
  begin
    if (slv = x"13") then
      result := CMD_READ;
    elsif (slv = x"23") then
      result := CMD_WRITE;
    elsif (slv = x"03") then
      result := CMD_READ_DATA;
    elsif (slv = x"55") then
      result := CMD_BREAK;
    elsif (slv = x"e7") then
      result := ESCAPE;
    elsif (slv = X"00") then
      result := CMD_NULL;
    else
      result := INVALID;
    end if;
    return result;
  end function;

  function to_slv (cmd : cmd_t) return std_logic_vector is
    variable result : std_logic_vector(BYTE_W-1 downto 0);
  begin
    case (cmd) is
      when CMD_READ =>
        result := x"13";
      when CMD_WRITE =>
        result := x"23";
      when CMD_READ_DATA =>
        result := x"03";
      when CMD_BREAK =>
        result := x"55";
      when ESCAPE =>
        result := x"e7";
      when CMD_NULL =>
        result := x"00";
      when INVALID =>
        result := (others => 'X');
    end case;
    return result;
  end function;

  signal reg_fsm : reg_fsm_t := AWAIT_ESC;

  constant NUM_ADDR_BYTES    : natural                                               := ADDR_W/BYTE_W;
  constant ADDR_IDX_W        : natural                                               := ceil_log2(NUM_ADDR_BYTES);
  signal addr_bytes          : array_slv_t(0 to NUM_ADDR_BYTES-1)(BYTE_W-1 downto 0) := (others => (others => '0'));
  signal addr_bytes_idx      : unsigned(ADDR_IDX_W-1 downto 0)                       := (others => '0');
  signal addr_bytes_idx_next : unsigned(ADDR_IDX_W downto 0);
  signal addr_bytes_rcvd     : std_logic := '0';
  signal wr_task             : std_logic := '0';

  signal rd_en_reg         : std_logic := '0';
  signal wr_en_reg         : std_logic := '0';
  signal byte_data_escaped : std_logic := '0';

  constant NUM_DATA_BYTES       : natural                                               := DATA_W/BYTE_W;
  constant DATA_IDX_W           : natural                                               := ceil_log2(NUM_DATA_BYTES);
  signal wr_data_bytes          : array_slv_t(0 to NUM_DATA_BYTES-1)(BYTE_W-1 downto 0) := (others => (others => '0'));
  signal wr_data_bytes_idx      : unsigned(DATA_IDX_W-1 downto 0)                       := (others => '0');
  signal wr_data_bytes_idx_next : unsigned(DATA_IDX_W downto 0);
  signal wr_data_bytes_rcvd     : std_logic := '0';

  signal rd_resp_fsm : rd_resp_fsm_t := AWAIT_RD_EN;

  signal rd_latency_counter     : unsigned(ceil_log2(RD_LATENCY) downto 0) := (others => '0');
  signal rd_data_bytes          : array_slv_t(0 to NUM_DATA_BYTES-1)(BYTE_W-1 downto 0);
  signal rd_data_bytes_idx      : unsigned(DATA_IDX_W-1 downto 0) := (others => '0');
  signal rd_data_bytes_idx_next : unsigned(DATA_IDX_W downto 0);
  signal rd_byte_data_escaped   : std_logic := '0';

  signal data_out_reg     : std_logic_vector(BYTE_W-1 downto 0) := (others => '0');
  signal data_out_vld_reg : std_logic                           := '0';

begin

  -- Next idxs combinational assignments
  addr_bytes_idx_next    <= resize(addr_bytes_idx, ADDR_IDX_W+1) + 1;
  wr_data_bytes_idx_next <= resize(wr_data_bytes_idx, DATA_IDX_W+1) + 1;
  rd_data_bytes_idx_next <= resize(rd_data_bytes_idx, DATA_IDX_W+1) + 1;

  -- Holding read bytes when valid.
  p_rd_data_bytes : process (all)
  begin
    if (rd_ack = '1') then
      rd_data_bytes <= reverse_array(to_array_slv(rd_data, BYTE_W, NUM_DATA_BYTES));
    end if;
  end process;

  p_clk : process (clk)
  begin
    if rising_edge(clk) then
      -- Cyclic assignments
      rd_en_reg        <= '0';
      wr_en_reg        <= '0';
      data_out_vld_reg <= '0';

      -- Parse commands from upstream then action them.
      case (reg_fsm) is
        when AWAIT_ESC =>
          if (data_in_vld = '1' and to_cmd(data_in) = ESCAPE) then
            reg_fsm <= PARSE_CMD;
          end if;

        -- Only valid commands will be parsed.
        -- Assert check to verify escape character assumption is held.
        when PARSE_CMD =>
          if (data_in_vld = '1') then
            case (to_cmd(data_in)) is
              when CMD_READ =>
                wr_task <= '0';
                reg_fsm <= PARSE_ADDR;
              when CMD_WRITE =>
                wr_task <= '1';
                reg_fsm <= PARSE_ADDR;
              when CMD_BREAK =>
                reg_fsm <= AWAIT_ESC;
              when ESCAPE =>
                assert (False) report "Received 2x escape characters at beginning of command byte stream. Ignoring..." severity WARNING;
                reg_fsm <= AWAIT_ESC;
              when others =>
                assert (FALSE)
                  report "Assumption violated! Escape characters in byte stream must "
                  & "be followed by another escape character (0xe7), break chatacter (0x55)"
                  & ", or another read/write command (0x13, 0x23). Got: 0x"
                  & to_hex_string(data_in)
                  severity FAILURE;
            end case;
          end if;

        -- Transitions to getting write data after parsing address bytes.
        -- Null bytes when valid means bytes have been received,
        -- but only pad MSB.
        -- Receiving ESCAPE + BREAK will send FSM back to AWAIT_ESC.
        -- Receiving ESCPAE + READ/WRITE command will clear any cleared bytes.
        when PARSE_ADDR =>
          if (data_in_vld = '1') then
            addr_bytes_rcvd <= '1';
            if (or data_in = '1' or addr_bytes_rcvd = '0') then
              if (byte_data_escaped = '0') then
                if (to_cmd(data_in) = ESCAPE) then
                  byte_data_escaped <= '1';
                else
                  addr_bytes(to_integer(addr_bytes_idx)) <= data_in;
                  addr_bytes_idx                         <= addr_bytes_idx + 1;

                  if (addr_bytes_idx_next >= NUM_ADDR_BYTES) then
                    addr_bytes_rcvd <= '0';
                    addr_bytes_idx  <= (others => '0');

                    if (wr_task = '1') then
                      reg_fsm <= PARSE_WRITE_DATA;
                    else
                      rd_en_reg <= '1';
                      reg_fsm   <= AWAIT_ESC;
                    end if;
                  end if;
                end if;
              elsif (byte_data_escaped = '1') then
                if (to_cmd(data_in) /= CMD_NULL) then
                  if (to_cmd(data_in) = CMD_BREAK) then
                    byte_data_escaped <= '0';
                    addr_bytes_idx    <= (others => '0');
                    reg_fsm           <= AWAIT_ESC;
                  elsif (to_cmd(data_in) = ESCAPE) then
                    addr_bytes(to_integer(addr_bytes_idx)) <= data_in;
                    addr_bytes_idx                         <= addr_bytes_idx + 1;
                    byte_data_escaped                      <= '0';

                    if (addr_bytes_idx_next >= NUM_ADDR_BYTES) then
                      addr_bytes_rcvd <= '0';
                      addr_bytes_idx  <= (others => '0');

                      if (wr_task = '1') then
                        reg_fsm <= PARSE_WRITE_DATA;
                      else
                        rd_en_reg <= '1';
                        reg_fsm   <= AWAIT_ESC;
                      end if;
                    end if;
                  elsif (to_cmd(data_in) /= ESCAPE) then
                    assert (FALSE)
                      report "Command change in the middle of parsing addresses!"
                      severity WARNING;

                    case (to_cmd(data_in)) is
                      when CMD_READ             =>
                        addr_bytes_idx <= (others => '0');
                        wr_task        <= '0';
                        reg_fsm        <= PARSE_ADDR;
                      when CMD_WRITE =>
                        addr_bytes_idx <= (others => '0');
                        wr_task        <= '1';
                        reg_fsm        <= PARSE_ADDR;
                      when others =>
                        assert (FALSE)
                          report "Assumption violated! Escape characters in byte stream must "
                          & "be followed by another escape character (0xe7), break chatacter (0x55)"
                          & ", or another read/write command (0x13, 0x23). Got: 0x"
                          & to_hex_string(data_in)
                          severity FAILURE;
                    end case;
                  end if;
                end if;
              end if;
            end if;
          end if;

        -- Pulse wr_en after parsing write data bytes.
        -- Receiving ESCAPE + BREAK will send FSM back to AWAIT_ESC.
        -- Receiving ESCPAE + READ/WRITE command will clear any cleared bytes.
        when PARSE_WRITE_DATA =>
          if (data_in_vld = '1') then
            wr_data_bytes_rcvd <= '1';
            if (or data_in = '1' or wr_data_bytes_rcvd = '0') then
              if (byte_data_escaped = '0') then
                if (to_cmd(data_in) = ESCAPE) then
                  byte_data_escaped <= '1';
                else
                  wr_data_bytes(to_integer(wr_data_bytes_idx)) <= data_in;
                  wr_data_bytes_idx                            <= wr_data_bytes_idx + 1;

                  if (wr_data_bytes_idx_next >= DATA_W/BYTE_W) then
                    wr_en_reg         <= '1';
                    wr_task           <= '0';
                    wr_data_bytes_idx <= (others => '0');
                    reg_fsm           <= AWAIT_ESC;
                  end if;
                end if;
              elsif (byte_data_escaped = '1') then
                if (to_cmd(data_in) /= CMD_NULL) then
                  if (to_cmd(data_in) = CMD_BREAK) then
                    byte_data_escaped <= '0';
                    wr_data_bytes_idx <= (others => '0');
                    reg_fsm           <= AWAIT_ESC;
                  elsif (to_cmd(data_in) = ESCAPE) then
                    wr_data_bytes(to_integer(wr_data_bytes_idx)) <= data_in;
                    wr_data_bytes_idx                            <= wr_data_bytes_idx + 1;
                    byte_data_escaped                            <= '0';

                    if (wr_data_bytes_idx_next >= DATA_W/BYTE_W) then
                      wr_en_reg         <= '1';
                      wr_task           <= '0';
                      wr_data_bytes_idx <= (others => '0');
                      reg_fsm           <= AWAIT_ESC;
                    end if;
                  elsif (to_cmd(data_in) /= ESCAPE) then
                    assert (FALSE)
                      report "Command change in the middle of a WRITE"
                      severity WARNING;

                    case (to_cmd(data_in)) is
                      when CMD_READ             =>
                        addr_bytes_idx <= (others => '0');
                        wr_task        <= '0';
                        reg_fsm        <= PARSE_ADDR;
                      when CMD_WRITE =>
                        addr_bytes_idx <= (others => '0');
                        wr_task        <= '1';
                        reg_fsm        <= PARSE_ADDR;
                      when others =>
                        assert (FALSE)
                          report "Assumption violated! Escape characters in byte stream must "
                          & "be followed by another escape character (0xe7), break chatacter (0x55)"
                          & ", or another read/write command (0x13, 0x23). Got: 0x"
                          & to_hex_string(data_in)
                          severity FAILURE;
                    end case;
                  end if;
                end if;
              end if;
            end if;
          end if;
      end case;

      -- Stream read bytes upstream after a successful read. 
      case (rd_resp_fsm) is
        when AWAIT_RD_EN =>
          if (rd_en_reg = '1') then
            rd_resp_fsm <= AWAIT_RD_ACK;
          end if;

        when AWAIT_RD_ACK =>
          rd_latency_counter <= rd_latency_counter + 1;

          if (rd_ack = '1') then
            data_out_reg       <= to_slv(ESCAPE);
            data_out_vld_reg   <= '1';
            rd_latency_counter <= (others => '0');
            rd_resp_fsm        <= OUTPUT_CMD_READ_DATA;
          end if;

          if (and rd_latency_counter) then
            data_out_reg       <= to_slv(ESCAPE);
            data_out_vld_reg   <= '1';
            rd_latency_counter <= (others => '0');
            rd_resp_fsm        <= OUTPUT_BREAK;
          end if;

        when OUTPUT_CMD_READ_DATA =>
          data_out_reg     <= to_slv(CMD_READ_DATA);
          data_out_vld_reg <= '1';
          rd_resp_fsm      <= OUTPUT_RD_RESP;

        when OUTPUT_RD_RESP =>
          data_out_reg      <= rd_data_bytes(to_integer(rd_data_bytes_idx));
          data_out_vld_reg  <= '1';
          rd_data_bytes_idx <= rd_data_bytes_idx + 1;
          -- NOTE: Use this to alleviate timing on less powerful hardware.
          -- rd_resp_fsm      <= PIPE_RD_DATA_BYTES_IDX;

          if (rd_byte_data_escaped = '0') then
            if (to_cmd(rd_data_bytes(to_integer(rd_data_bytes_idx))) = ESCAPE) then
              rd_byte_data_escaped <= '1';
              rd_data_bytes_idx    <= rd_data_bytes_idx;
            else
              if (rd_data_bytes_idx_next >= DATA_W/BYTE_W) then
                rd_byte_data_escaped <= '0';
                rd_data_bytes_idx    <= (others => '0');
                rd_resp_fsm          <= AWAIT_RD_EN;
              end if;
            end if;
          elsif (rd_byte_data_escaped = '1') then
            rd_byte_data_escaped <= '0';

            if (rd_data_bytes_idx_next >= DATA_W/BYTE_W) then
              rd_byte_data_escaped <= '0';
              rd_data_bytes_idx    <= (others => '0');
              rd_resp_fsm          <= AWAIT_RD_EN;
            end if;
          end if;

        when PIPE_RD_DATA_BYTES_IDX =>
          rd_resp_fsm      <= OUTPUT_RD_RESP;

        when OUTPUT_BREAK =>
          data_out_reg     <= to_slv(CMD_BREAK);
          data_out_vld_reg <= '1';
          rd_resp_fsm      <= AWAIT_RD_EN;

      end case;

      if (reset = '1') then
        rd_en_reg          <= '0';
        wr_en_reg          <= '0';
        wr_task            <= '0';
        byte_data_escaped  <= '0';
        addr_bytes_idx     <= (others => '0');
        wr_data_bytes_idx  <= (others => '0');
        rd_latency_counter <= (others => '0');
        rd_data_bytes_idx  <= (others => '0');
        data_out_reg       <= (others => '0');
        data_out_vld_reg   <= '0';
        reg_fsm            <= AWAIT_ESC;
        rd_resp_fsm        <= AWAIT_RD_EN;
      end if;
    end if;
  end process;

  -- Outputs
  addr         <= to_flat_slv(reverse_array(addr_bytes));
  wr_data      <= to_flat_slv(reverse_array(wr_data_bytes));
  rd_en        <= rd_en_reg;
  wr_en        <= wr_en_reg;
  data_out     <= data_out_reg;
  data_out_vld <= data_out_vld_reg;

end rtl;