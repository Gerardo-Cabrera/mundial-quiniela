import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import { groupMatchesByDay, isFirstGoalHit, type Match } from "@/types";

function match(id: number, match_date: string): Match {
  return {
    id,
    api_fixture_id: id,
    home_team: "A",
    away_team: "B",
    home_team_logo: null,
    away_team_logo: null,
    home_score: null,
    away_score: null,
    elapsed: null,
    first_goal_team: null,
    first_goal_player_id: null,
    first_goal_player: null,
    phase: "group_stage",
    status: "scheduled",
    match_date,
  };
}

describe("isFirstGoalHit", () => {
  it("acierta cuando el id del goleador pronosticado y el real coinciden", () => {
    expect(isFirstGoalHit({ first_goal_player_id: 10 }, { first_goal_player_id: 10 })).toBe(true);
  });

  it("falla cuando los ids difieren", () => {
    expect(isFirstGoalHit({ first_goal_player_id: 10 }, { first_goal_player_id: 20 })).toBe(false);
  });

  it("falla si falta el pronóstico o el real (null nunca cuenta como acierto)", () => {
    expect(isFirstGoalHit({ first_goal_player_id: null }, { first_goal_player_id: 10 })).toBe(false);
    expect(isFirstGoalHit({ first_goal_player_id: 10 }, { first_goal_player_id: null })).toBe(false);
    expect(isFirstGoalHit({ first_goal_player_id: null }, { first_goal_player_id: null })).toBe(false);
  });
});

describe("groupMatchesByDay", () => {
  // now fijo (TZ=UTC en el script de test) para que el cierre de jornada sea determinista.
  const NOW = new Date("2026-06-22T12:00:00Z");
  beforeEach(() => {
    vi.useFakeTimers();
    vi.setSystemTime(NOW);
  });
  afterEach(() => vi.useRealTimers());

  it("agrupa por día, ordena los días y, dentro del día, por hora de inicio", () => {
    const days = groupMatchesByDay([
      match(1, "2026-06-23T18:00:00Z"),
      match(2, "2026-06-22T20:00:00Z"),
      match(3, "2026-06-22T16:00:00Z"),
    ]);
    expect(days.map((d) => d.day)).toEqual(["2026-06-22", "2026-06-23"]);
    expect(days[0].matches.map((m) => m.id)).toEqual([3, 2]); // 16:00 antes que 20:00
    expect(days[0].firstKickoff).toBe(+new Date("2026-06-22T16:00:00Z"));
  });

  it("jornada ABIERTA si el primer partido es a más de 1 h", () => {
    const [d] = groupMatchesByDay([match(1, "2026-06-22T18:00:00Z")]); // now=12:00 → +6 h
    expect(d.open).toBe(true);
  });

  it("jornada CERRADA dentro de la hora previa al primer partido", () => {
    const [d] = groupMatchesByDay([match(1, "2026-06-22T12:30:00Z")]); // +30 min < 1 h
    expect(d.open).toBe(false);
  });

  it("cierra por el PRIMER partido del día aunque haya partidos posteriores (regresión §22)", () => {
    const [d] = groupMatchesByDay([
      match(1, "2026-06-22T11:00:00Z"), // ya empezó (now=12:00)
      match(2, "2026-06-22T19:00:00Z"), // aún en el futuro
    ]);
    expect(d.open).toBe(false); // el cierre usa el primer kickoff, no el último
  });
});
